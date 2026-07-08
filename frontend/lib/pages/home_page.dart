import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

class HomePage extends StatelessWidget {
  const HomePage({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: const Text('Time Manager')),
      drawer: _buildDrawer(context),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.today_rounded, size: 80, color: theme.colorScheme.primary),
              const SizedBox(height: 16),
              Text('今日概览', style: theme.textTheme.headlineSmall),
              const SizedBox(height: 8),
              Text('欢迎使用 Time Manager', style: theme.textTheme.bodyLarge?.copyWith(color: theme.colorScheme.onSurfaceVariant)),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildDrawer(BuildContext context) {
    final theme = Theme.of(context);
    return Drawer(
      child: ListView(
        children: [
          DrawerHeader(
            decoration: BoxDecoration(color: theme.colorScheme.primaryContainer),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                Icon(Icons.access_time_rounded, size: 48, color: theme.colorScheme.onPrimaryContainer),
                const SizedBox(height: 8),
                Text('Time Manager', style: theme.textTheme.titleLarge?.copyWith(color: theme.colorScheme.onPrimaryContainer)),
              ],
            ),
          ),
          ListTile(leading: const Icon(Icons.home), title: const Text('首页'), onTap: () { Navigator.pop(context); }),
          ListTile(leading: const Icon(Icons.event), title: const Text('日程'), onTap: () { Navigator.pop(context); context.go('/events'); }),
          ListTile(leading: const Icon(Icons.checklist), title: const Text('待办'), onTap: () { Navigator.pop(context); context.go('/tasks'); }),
          ListTile(leading: const Icon(Icons.flag), title: const Text('目标'), onTap: () { Navigator.pop(context); context.go('/goals'); }),
          const Divider(),
          ListTile(leading: const Icon(Icons.auto_awesome), title: const Text('AI 助手'), onTap: () { Navigator.pop(context); context.go('/ai-assistant'); }),
          ListTile(leading: const Icon(Icons.bar_chart), title: const Text('统计报告'), onTap: () { Navigator.pop(context); context.go('/reports'); }),
          const Divider(),
          ListTile(leading: const Icon(Icons.settings), title: const Text('设置'), onTap: () { Navigator.pop(context); context.go('/settings'); }),
          ListTile(leading: const Icon(Icons.system_update), title: const Text('更新'), onTap: () { Navigator.pop(context); context.go('/update'); }),
        ],
      ),
    );
  }
}