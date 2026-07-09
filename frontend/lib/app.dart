import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:go_router/go_router.dart';

import 'pages/login_page.dart';
import 'pages/register_page.dart';
import 'pages/home_page.dart';
import 'pages/events_page.dart';
import 'pages/tasks_page.dart';
import 'pages/goals_page.dart';
import 'pages/ai_assistant_page.dart';
import 'pages/settings_page.dart';
import 'pages/reports_page.dart';
import 'pages/update_page.dart';
import 'theme.dart';

final _router = GoRouter(
  initialLocation: '/login',
  routes: [
    GoRoute(path: '/login', builder: (_, __) => const LoginPage()),
    GoRoute(path: '/register', builder: (_, __) => const RegisterPage()),
    GoRoute(path: '/home', builder: (_, __) => const HomePage()),
    GoRoute(path: '/events', builder: (_, __) => const EventsPage()),
    GoRoute(path: '/tasks', builder: (_, __) => const TasksPage()),
    GoRoute(path: '/goals', builder: (_, __) => const GoalsPage()),
    GoRoute(path: '/ai-assistant', builder: (_, __) => const AiAssistantPage()),
    GoRoute(path: '/settings', builder: (_, __) => const SettingsPage()),
    GoRoute(path: '/reports', builder: (_, __) => const ReportsPage()),
    GoRoute(path: '/update', builder: (_, __) => const UpdatePage()),
  ],
);

class TimeManagerApp extends StatelessWidget {
  const TimeManagerApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'Time Manager',
      theme: AppTheme.light,
      darkTheme: AppTheme.dark,
      themeMode: ThemeMode.system,
      routerConfig: _router,
      debugShowCheckedModeBanner: false,
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      supportedLocales: const [
        Locale('zh', 'CN'),
        Locale('en', 'US'),
      ],
    );
  }
}
