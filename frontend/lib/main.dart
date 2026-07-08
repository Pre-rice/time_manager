import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'app.dart';
import 'services/api_service.dart';
import 'providers/auth_provider.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // 创建一个全局 ApiService 实例并加载已保存的 token
  final apiService = ApiService();
  await apiService.loadToken();

  runApp(
    ProviderScope(
      overrides: [
        apiServiceProvider.overrideWithValue(apiService),
      ],
      child: const TimeManagerApp(),
    ),
  );
}
