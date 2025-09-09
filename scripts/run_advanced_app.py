#!/usr/bin/env python3
"""
Cross-platform Python script to run the advanced Streamlit app with proper configuration.
Uses temp/.streamlit/config.toml for branding and stores all runtime files in temp/
"""
import os
import sys
import signal
import subprocess
import argparse
from pathlib import Path


def setup_directories():
    """Ensure temp directories exist"""
    temp_dir = Path("temp")
    run_dir = temp_dir / ".run"
    streamlit_dir = temp_dir / ".streamlit"
    
    temp_dir.mkdir(exist_ok=True)
    run_dir.mkdir(exist_ok=True)
    streamlit_dir.mkdir(exist_ok=True)
    
    return run_dir, streamlit_dir


def kill_existing_process(pid_file: Path):
    """Kill existing process if running"""
    if pid_file.exists():
        try:
            with open(pid_file, 'r') as f:
                pid = int(f.read().strip())
            
            # Cross-platform process kill
            if os.name == 'nt':  # Windows
                subprocess.run(['taskkill', '/F', '/PID', str(pid)], 
                             capture_output=True, check=False)
            else:  # Unix/Linux/macOS
                os.kill(pid, signal.SIGTERM)
            
            print(f"✅ Stopped existing process (PID: {pid})")
        except (ValueError, ProcessLookupError, FileNotFoundError):
            pass
        finally:
            pid_file.unlink(missing_ok=True)


def run_streamlit_app(port: int, run_dir: Path, streamlit_dir: Path):
    """Run Streamlit app with proper configuration"""
    # Correct path to the advanced app within src/
    app_file = "src/apps/app_advanced.py"
    pid_file = run_dir / f"streamlit_advanced.{port}.pid"
    log_file = run_dir / f"streamlit_advanced.{port}.log"
    
    # Kill existing process
    kill_existing_process(pid_file)
    
    # Set environment variable for Streamlit config
    env = os.environ.copy()
    env['STREAMLIT_CONFIG_DIR'] = str(streamlit_dir)
    
    # Build command
    cmd = [
        sys.executable, "-m", "streamlit", "run", app_file,
        "--server.address", "127.0.0.1",
        "--server.port", str(port),
        "--server.headless", "true",
        "--global.developmentMode", "false"
    ]
    
    print(f"🚀 Starting advanced Streamlit app on port {port}...")
    print(f"📊 Using config: {streamlit_dir / 'config.toml'}")
    print(f"📝 Logs: {log_file}")
    
    try:
        # Start process
        with open(log_file, 'w') as log:
            process = subprocess.Popen(
                cmd, 
                stdout=log, 
                stderr=subprocess.STDOUT,
                env=env,
                cwd=Path.cwd()
            )
        
        # Save PID
        with open(pid_file, 'w') as f:
            f.write(str(process.pid))
        
        print(f"✅ Advanced app started successfully!")
        print(f"🌐 Access at: http://127.0.0.1:{port}")
        print(f"🆔 Process ID: {process.pid}")
        print(f"📁 Runtime files in: {run_dir}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to start app: {e}")
        return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Run advanced Streamlit app with branding")
    parser.add_argument("--port", "-p", type=int, default=8502, 
                       help="Port to run on (default: 8502)")
    parser.add_argument("--kill", "-k", action="store_true",
                       help="Kill existing process and exit")
    
    args = parser.parse_args()
    
    # Setup directories
    run_dir, streamlit_dir = setup_directories()
    
    # Kill mode
    if args.kill:
        pid_file = run_dir / f"streamlit_advanced.{args.port}.pid"
        kill_existing_process(pid_file)
        print("🛑 Process killed")
        return
    
    # Check if config exists
    config_file = streamlit_dir / "config.toml"
    if not config_file.exists():
        print(f"⚠️  Warning: {config_file} not found - using default styling")
    
    # Run app
    success = run_streamlit_app(args.port, run_dir, streamlit_dir)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
