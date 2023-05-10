from app import socketio, app

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=10900, allow_unsafe_werkzeug=True)