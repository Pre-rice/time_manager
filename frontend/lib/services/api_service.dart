import 'package:dio/dio.dart';
import 'package:shared_preferences/shared_preferences.dart';

class ApiService {
  static const String defaultBaseUrl = 'http://localhost:8000';
  static const String _tokenKey = 'auth_token';

  final Dio _dio;
  String? _token;

  ApiService({String baseUrl = defaultBaseUrl})
      : _dio = Dio(BaseOptions(
          baseUrl: baseUrl,
          connectTimeout: const Duration(seconds: 10),
          receiveTimeout: const Duration(seconds: 10),
          headers: {'Content-Type': 'application/json'},
        )) {
    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) {
        if (_token != null) {
          options.headers['Authorization'] = 'Bearer $_token';
        }
        handler.next(options);
      },
      onError: (error, handler) {
        if (error.response?.statusCode == 401) {
          clearToken();
        }
        handler.next(error);
      },
    ));
  }

  Future<void> loadToken() async {
    final prefs = await SharedPreferences.getInstance();
    _token = prefs.getString(_tokenKey);
  }

  bool get hasToken => _token != null;

  Future<void> saveToken(String token) async {
    _token = token;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_tokenKey, token);
  }

  Future<void> clearToken() async {
    _token = null;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_tokenKey);
  }

  // ==================== 认证 ====================

  Future<Map<String, dynamic>> login(String username, String password) async {
    final response = await _dio.post('/api/v1/auth/login', data: {
      'username': username,
      'password': password,
    });
    return response.data;
  }

  Future<Map<String, dynamic>> register(String username, String email, String password) async {
    final response = await _dio.post('/api/v1/auth/register', data: {
      'username': username,
      'email': email,
      'password': password,
    });
    return response.data;
  }

  // ==================== 日程 ====================

  Future<List<dynamic>> getEvents({String? start, String? end}) async {
    final query = <String, dynamic>{};
    if (start != null) query['start'] = start;
    if (end != null) query['end'] = end;
    final response = await _dio.get('/api/v1/events/', queryParameters: query);
    return response.data as List<dynamic>;
  }

  Future<Map<String, dynamic>> createEvent(Map<String, dynamic> data) async {
    final response = await _dio.post('/api/v1/events/', data: data);
    return response.data;
  }

  Future<Map<String, dynamic>> updateEvent(String id, Map<String, dynamic> data) async {
    final response = await _dio.put('/api/v1/events/$id', data: data);
    return response.data;
  }

  Future<void> deleteEvent(String id) async {
    await _dio.delete('/api/v1/events/$id');
  }

  // ==================== 待办 ====================

  Future<List<dynamic>> getTasks() async {
    final response = await _dio.get('/api/v1/tasks/');
    return response.data as List<dynamic>;
  }

  Future<Map<String, dynamic>> createTask(Map<String, dynamic> data) async {
    final response = await _dio.post('/api/v1/tasks/', data: data);
    return response.data;
  }

  Future<Map<String, dynamic>> updateTask(String id, Map<String, dynamic> data) async {
    final response = await _dio.put('/api/v1/tasks/$id', data: data);
    return response.data;
  }

  Future<void> deleteTask(String id) async {
    await _dio.delete('/api/v1/tasks/$id');
  }

  // ==================== 目标 ====================

  Future<List<dynamic>> getGoals() async {
    final response = await _dio.get('/api/v1/goals/');
    return response.data as List<dynamic>;
  }

  Future<Map<String, dynamic>> createGoal(Map<String, dynamic> data) async {
    final response = await _dio.post('/api/v1/goals/', data: data);
    return response.data;
  }

  Future<Map<String, dynamic>> updateGoal(String id, Map<String, dynamic> data) async {
    final response = await _dio.put('/api/v1/goals/$id', data: data);
    return response.data;
  }

  Future<Map<String, dynamic>> updateGoalProgress(String id, double currentValue) async {
    final response = await _dio.patch('/api/v1/goals/$id/progress', data: {
      'current_value': currentValue,
    });
    return response.data;
  }

  Future<void> deleteGoal(String id) async {
    await _dio.delete('/api/v1/goals/$id');
  }

  // ==================== AI 配置 ====================

  Future<Map<String, dynamic>?> getAIConfig() async {
    try {
      final response = await _dio.get('/api/v1/ai/config/');
      return response.data as Map<String, dynamic>?;
    } catch (_) {
      return null;
    }
  }

  Future<Map<String, dynamic>> saveAIConfig(Map<String, dynamic> data) async {
    final response = await _dio.put('/api/v1/ai/config/', data: data);
    return response.data;
  }

  Future<void> deleteAIConfig() async {
    await _dio.delete('/api/v1/ai/config/');
  }

  // ==================== AI 功能 ====================

  Future<List<dynamic>> extractFromText(String text) async {
    final response = await _dio.post('/api/v1/ai/extract', data: {
      'text': text,
    });
    return response.data['items'] as List<dynamic>;
  }

  Future<Map<String, dynamic>> suggestTime(String title, int durationMinutes) async {
    final response = await _dio.post('/api/v1/ai/suggest-time', data: {
      'title': title,
      'duration_minutes': durationMinutes,
    });
    return response.data;
  }

  Future<Map<String, dynamic>> getMorningMessage() async {
    final response = await _dio.get('/api/v1/ai/morning-message');
    return response.data;
  }
}