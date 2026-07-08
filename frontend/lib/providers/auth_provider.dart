import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/api_service.dart';

final apiServiceProvider = Provider<ApiService>((ref) {
  return ApiService();
});

final authProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  return AuthNotifier(ref.read(apiServiceProvider));
});

class AuthState {
  final bool isAuthenticated;
  final bool isLoading;
  final String? error;
  final String? username;

  const AuthState({
    this.isAuthenticated = false,
    this.isLoading = false,
    this.error,
    this.username,
  });

  AuthState copyWith({
    bool? isAuthenticated,
    bool? isLoading,
    String? error,
    String? username,
  }) {
    return AuthState(
      isAuthenticated: isAuthenticated ?? this.isAuthenticated,
      isLoading: isLoading ?? this.isLoading,
      error: error,
      username: username ?? this.username,
    );
  }
}

class AuthNotifier extends StateNotifier<AuthState> {
  final ApiService _apiService;

  AuthNotifier(this._apiService)
      : super(AuthState(isAuthenticated: _apiService.hasToken));

  Future<bool> login(String username, String password) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final result = await _apiService.login(username, password);
      final token = result['access_token'] as String;
      await _apiService.saveToken(token);
      state = state.copyWith(
        isAuthenticated: true,
        isLoading: false,
        username: username,
      );
      return true;
    } catch (e) {
      int? status;
      if (e is DioException) {
        status = e.response?.statusCode;
        if (status == 401) {
          state = state.copyWith(isLoading: false, error: '用户名或密码错误');
          return false;
        }
      }
      state = state.copyWith(isLoading: false, error: '登录失败，请检查用户名和密码');
      return false;
    }
  }

  Future<bool> register(String username, String email, String password) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      await _apiService.register(username, email, password);
      state = state.copyWith(isLoading: false);
      return true;
    } catch (e) {
      int? status;
      if (e is DioException) {
        status = e.response?.statusCode;
        if (status == 409) {
          final data = e.response?.data;
          String msg = '用户名或邮箱已被注册';
          if (data is Map && data.containsKey('detail')) {
            msg = data['detail'].toString();
          }
          state = state.copyWith(isLoading: false, error: msg);
          return false;
        }
        if (status == 422) {
          // Pydantic 验证错误，detail 是数组
          final data = e.response?.data;
          String msg = '输入数据格式不正确';
          if (data is Map && data['detail'] is List) {
            final detail = data['detail'] as List;
            if (detail.isNotEmpty && detail[0] is Map) {
              final first = detail[0] as Map;
              // 提取具体错误描述
              msg = first['msg']?.toString() ?? msg;
            }
          }
          state = state.copyWith(isLoading: false, error: msg);
          return false;
        }
      }
      state = state.copyWith(isLoading: false, error: '注册失败，请稍后重试');
      return false;
    }
  }

  Future<void> logout() async {
    await _apiService.clearToken();
    state = const AuthState();
  }
}