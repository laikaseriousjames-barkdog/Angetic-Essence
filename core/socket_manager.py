from flask_socketio import SocketIO

# Global SocketIO instance to avoid circular imports between app.py and base_agent.py
socketio = SocketIO(cors_allowed_origins="*")

def init_socketio(app):
    socketio.init_app(app)