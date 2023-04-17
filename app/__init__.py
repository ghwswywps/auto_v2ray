from .routers import bp as routers_bp
from .main import app, socketio
from .socket_handlers import get_instance

app.register_blueprint(routers_bp)
socketio.on_event('my_event', get_instance)
