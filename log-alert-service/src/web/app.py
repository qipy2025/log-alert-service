from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO
import os
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

load_dotenv()

# 全局 AlertService 实例
_alert_service_instance = None

def set_alert_service_instance(instance):
    """设置 AlertService 全局实例"""
    global _alert_service_instance
    _alert_service_instance = instance
    logger.info("AlertService 实例已设置到全局")

def get_alert_service_instance():
    """获取 AlertService 全局实例"""
    return _alert_service_instance

def create_app(testing=False):
    """创建Flask应用"""
    # 确定静态文件路径
    static_folder = None
    if not testing:
        # 尝试找到构建后的前端文件
        possible_paths = [
            os.path.join(os.path.dirname(__file__), '../../frontend/dist'),
            os.path.join(os.path.dirname(__file__), '../frontend/dist'),
        ]
        for path in possible_paths:
            if os.path.exists(path):
                static_folder = path
                break

    app = Flask(__name__,
                static_folder=static_folder,
                static_url_path='/')

    # 配置
    app.config['TESTING'] = testing
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')

    # 启用CORS
    CORS(app)

    # 初始化SocketIO
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
    app.extensions['socketio'] = socketio

    # 注册路由
    from .routes import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')

    # 注册SocketIO事件
    from .socketio import register_socketio_events
    register_socketio_events(socketio)

    # 错误处理
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found'}), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'Internal server error'}), 500

    # SPA路由支持
    @app.route('/')
    def index():
        if static_folder:
            import os
            index_path = os.path.join(static_folder, 'index.html')
            if os.path.exists(index_path):
                return send_from_directory(static_folder, 'index.html')
        return jsonify({'message': '设备监控API服务运行中'})

    @app.route('/health')
    def health():
        """健康检查端点"""
        return jsonify({'status': 'healthy', 'service': 'device-monitoring'})

    logger.info("Flask应用创建完成")
    return app
