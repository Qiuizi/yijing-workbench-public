use std::{
    io::{Read, Write},
    net::{TcpListener, TcpStream, SocketAddr},
    process::{Child, Command, Stdio},
    sync::{Arc, Mutex},
    thread,
    time::{Duration, Instant},
};

use serde::Serialize;
use tauri::{Manager, State, path::BaseDirectory};

#[derive(Clone, Default)]
struct BackendState {
    runtime: Arc<Mutex<BackendRuntime>>,
}

#[derive(Default)]
struct BackendRuntime {
    child: Option<Child>,
    port: Option<u16>,
    token: Option<String>,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct BackendConnection {
    base_url: String,
    token: String,
}

fn random_token() -> Result<String, String> {
    let mut bytes = [0_u8; 32];
    getrandom::fill(&mut bytes).map_err(|_| "无法创建本地 API 鉴权令牌".to_string())?;
    Ok(bytes.iter().map(|byte| format!("{byte:02x}")).collect())
}

fn reserve_port() -> Result<(TcpListener, SocketAddr), String> {
    let listener = TcpListener::bind("127.0.0.1:0")
        .map_err(|_| "无法分配本地服务端口".to_string())?;
    let address = listener.local_addr().map_err(|_| "无法读取本地服务端口".to_string())?;
    Ok((listener, address))
}

fn healthy(port: u16, token: &str) -> bool {
    let address = SocketAddr::from(([127, 0, 0, 1], port));
    let Ok(mut stream) = TcpStream::connect_timeout(&address, Duration::from_millis(250)) else {
        return false;
    };
    let _ = stream.set_read_timeout(Some(Duration::from_millis(500)));
    let request = format!(
        "GET /api/desktop/health HTTP/1.1\r\nHost: 127.0.0.1\r\nAuthorization: Bearer {token}\r\nConnection: close\r\n\r\n"
    );
    if stream.write_all(request.as_bytes()).is_err() {
        return false;
    }
    let mut response = Vec::new();
    if stream.read_to_end(&mut response).is_err() {
        return false;
    }
    let response = String::from_utf8_lossy(&response);
    response.starts_with("HTTP/1.1 200 ") && response.contains("\"mode\":\"desktop\"")
}

fn ensure_backend(app: &tauri::AppHandle, state: &BackendState) -> Result<BackendConnection, String> {
    let mut runtime = state.runtime.lock().map_err(|_| "本地服务状态不可用".to_string())?;
    if let (Some(port), Some(token)) = (runtime.port, runtime.token.clone()) {
        let process_running = runtime.child.as_mut().and_then(|child| child.try_wait().ok()).is_some_and(|status| status.is_none());
        if process_running && healthy(port, &token) {
            return Ok(BackendConnection { base_url: format!("http://127.0.0.1:{port}"), token });
        }
    }

    if let Some(mut child) = runtime.child.take() {
        let _ = child.kill();
    }
    runtime.port = None;
    runtime.token = None;

    let app_data = app.path().app_local_data_dir()
        .map_err(|_| "无法定位 Windows 用户数据目录".to_string())?;
    std::fs::create_dir_all(&app_data).map_err(|_| "无法创建 Windows 用户数据目录".to_string())?;
    let backups = app_data.join("backups");
    std::fs::create_dir_all(&backups).map_err(|_| "无法创建用户数据备份目录".to_string())?;

    let log_path = app_data.join("yijing-backend.log");

    let sidecar_path = app.path().resolve(
        "binaries/yijing-backend/yijing-backend.exe",
        BaseDirectory::Resource,
    ).map_err(|_| "找不到已打包的 Python 后端 sidecar".to_string())?;
    if !sidecar_path.is_file() {
        return Err(format!("Python 后端文件缺失：{}", sidecar_path.display()));
    }
    let mut last_failure = "未获得可用的本地端口".to_string();
    for attempt in 1..=3 {
        // Reserve an ephemeral loopback port. If another process wins the small
        // release-to-bind race, the health probe and child status trigger a retry.
        let (listener, address) = match reserve_port() {
            Ok(reserved) => reserved,
            Err(_) => {
                last_failure = "无法分配本地端口".to_string();
                continue;
            }
        };
        let port = address.port();
        drop(listener);
        let token = random_token()?;

        let mut command = Command::new(&sidecar_path);
        command
            .current_dir(&app_data)
            .env("YIJING_SERVER_PORT", port.to_string())
            .env("YIJING_API_TOKEN", &token)
            .env("YIJING_DESKTOP_DEV", if cfg!(debug_assertions) { "1" } else { "0" })
            .env("YIJING_DB_PATH", app_data.join("history.sqlite3"))
            .env("YIJING_LOG_PATH", &log_path)
            .env("YIJING_BACKUP_DIR", &backups)
            .stdin(Stdio::null())
            .stdout(Stdio::null())
            .stderr(Stdio::null());
        #[cfg(windows)]
        {
            use std::os::windows::process::CommandExt;
            command.creation_flags(0x0800_0000); // CREATE_NO_WINDOW
        }
        let child = match command.spawn() {
            Ok(child) => child,
            Err(_) => {
                last_failure = format!("第 {attempt} 次启动 sidecar 失败");
                continue;
            }
        };
        runtime.child = Some(child);

        let started = Instant::now();
        while started.elapsed() < Duration::from_secs(8) {
            if healthy(port, &token) {
                runtime.port = Some(port);
                runtime.token = Some(token.clone());
                return Ok(BackendConnection { base_url: format!("http://127.0.0.1:{port}"), token });
            }
            let child_exited = runtime.child.as_mut()
                .and_then(|child| child.try_wait().ok())
                .flatten()
                .is_some();
            if child_exited {
                last_failure = format!("第 {attempt} 次 sidecar 未能绑定端口 {port}");
                runtime.child.take();
                break;
            }
            thread::sleep(Duration::from_millis(150));
        }

        if let Some(mut child) = runtime.child.take() {
            let _ = child.kill();
            let _ = child.wait();
        }
        if started.elapsed() >= Duration::from_secs(8) {
            last_failure = format!("第 {attempt} 次 sidecar 健康检查超时");
        }
    }
    runtime.port = None;
    runtime.token = None;
    Err(format!("本地 Python 后端连续 3 次启动失败（{last_failure}）。请检查本机日志：{}", log_path.display()))
}

#[tauri::command]
async fn backend_connection(app: tauri::AppHandle, state: State<'_, BackendState>) -> Result<BackendConnection, String> {
    let state = state.inner().clone();
    tauri::async_runtime::spawn_blocking(move || ensure_backend(&app, &state))
        .await
        .map_err(|_| "无法检查本地服务状态".to_string())?
}

fn stop_backend(app: &tauri::AppHandle) {
    if let Some(state) = app.try_state::<BackendState>() {
        if let Ok(mut runtime) = state.runtime.lock() {
            if let Some(mut child) = runtime.child.take() {
                let _ = child.kill();
            }
            runtime.port = None;
            runtime.token = None;
        }
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let builder = tauri::Builder::default()
        // Register this first so a second launch focuses this window instead of spawning another API.
        .plugin(tauri_plugin_single_instance::init(|app, _argv, _cwd| {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.unminimize();
                let _ = window.show();
                let _ = window.set_focus();
            }
        }))
    .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_log::Builder::new().level(log::LevelFilter::Warn).build())
        .manage(BackendState::default())
        .invoke_handler(tauri::generate_handler![backend_connection]);

    builder
        .build(tauri::generate_context!())
        .expect("failed to build Tauri application")
        .run(|app, event| {
            if matches!(event, tauri::RunEvent::Exit) {
                stop_backend(app);
            }
        });
}
