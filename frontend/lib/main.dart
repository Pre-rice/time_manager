import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import 'app.dart';
import 'services/api_service.dart';
import 'providers/auth_provider.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // 设置默认语言为中文，确保 DateFormat 和 TableCalendar 中文本地化正常
  Intl.defaultLocale = 'zh_CN';

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