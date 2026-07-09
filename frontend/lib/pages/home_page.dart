import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import '../services/api_service.dart';
import '../providers/auth_provider.dart';

final _homeDataProvider = FutureProvider.autoDispose<_HomeData>((ref) async {
  ref.watch(authProvider);
  final api = ref.read(apiServiceProvider);
  if (!api.hasToken) return _HomeData.empty;

  try {
    final events = await api.getEvents();
    final tasks = await api.getTasks();
    final goals = await api.getGoals();

    final today = DateFormat('yyyy-MM-dd').format(DateTime.now());
    final todayEvents = <Map<String, dynamic>>[];
    final undoneTasks = <Map<String, dynamic>>[];

    for (final e in events) {
      if (e is Map) {
        final m = Map<String, dynamic>.from(e);
        final start = m['start_time'] as String?;
        if (start != null && start.startsWith(today)) {
          todayEvents.add(m);
        }
      }
    }

    for (final t in tasks) {
      if (t is Map && t['status'] != 'done') {
        undoneTasks.add(Map<String, dynamic>.from(t));
      }
    }

    return _HomeData(
      events: events.map((e) => Map<String, dynamic>.from(e as Map)).toList(),
      tasks: tasks.map((e) => Map<String, dynamic>.from(e as Map)).toList(),
      goals: goals.map((e) => Map<String, dynamic>.from(e as Map)).toList(),
      todayEvents: todayEvents,
      undoneTasks: undoneTasks,
    );
  } catch (_) {
    return _HomeData.empty;
  }
});

class _HomeData {
  final List<Map<String, dynamic>> events;
  final List<Map<String, dynamic>> tasks;
  final List<Map<String, dynamic>> goals;
  final List<Map<String, dynamic>> todayEvents;
  final List<Map<String, dynamic>> undoneTasks;

  const _HomeData({
    required this.events,
    required this.tasks,
    required this.goals,
    required this.todayEvents,
    required this.undoneTasks,
  });

  static const empty = _HomeData(events: [], tasks: [], goals: [], todayEvents: [], undoneTasks: []);
}

class HomePage extends ConsumerStatefulWidget {
  const HomePage({super.key});

  @override
  ConsumerState<HomePage> createState() => _HomePageState();
}

class _HomePageState extends ConsumerState<HomePage> {
  String? _morningMessage;
  bool _loadingMessage = false;
  bool _syncingFudan = false;
  String? _fudanSyncResult;

  @override
  void initState() {
    super.initState();
    _autoSyncFudan();
  }

  Future<void> _autoSyncFudan() async {
    final api = ref.read(apiServiceProvider);
    if (!api.hasToken) return;

    // 检查复旦连接状态
    final status = await api.getFudanStatus();
    if (status['connected'] != true) return;

    // 有连接则自动同步
    setState(() => _syncingFudan = true);
    try {
      final result = await api.syncFudan();
      if (mounted) {
        if (result['success'] == true) {
          final data = result['data'] as Map?;
          if (data != null) {
            final created = data['events_created'] ?? 0;
            final tasks = data['tasks_created'] ?? 0;
            if ((created as int) > 0 || (tasks as int) > 0) {
              setState(() => _fudanSyncResult = '已同步 $created 个日程、$tasks 个待办');
              ref.invalidate(_homeDataProvider);
            }
          }
        }
      }
    } catch (_) {
      // 静默失败，不影响首页加载
    } finally {
      if (mounted) setState(() => _syncingFudan = false);
    }
  }

  Future<void> _generateMorningMessage() async {
    setState(() {
      _loadingMessage = true;
      _morningMessage = null;
    });
    try {
      final api = ref.read(apiServiceProvider);
      final result = await api.getMorningMessage();
      setState(() => _morningMessage = result['message'] as String?);
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('生成失败，请检查AI配置')),
        );
      }
    } finally {
      if (mounted) setState(() => _loadingMessage = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final homeData = ref.watch(_homeDataProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Time Manager')),
      drawer: _buildDrawer(context),
      body: RefreshIndicator(
        onRefresh: () async => ref.invalidate(_homeDataProvider),
        child: homeData.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (_, __) => const Center(child: Text('加载失败')),
          data: (data) => SingleChildScrollView(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Icon(Icons.wb_sunny, color: theme.colorScheme.primary),
                            const SizedBox(width: 8),
                            Text('今日梳理', style: theme.textTheme.titleMedium),
                            const Spacer(),
                            if (_morningMessage == null)
                              FilledButton.tonalIcon(
                                icon: _loadingMessage
                                    ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                                    : const Icon(Icons.auto_awesome, size: 16),
                                label: Text(_loadingMessage ? '生成中...' : 'AI 生成'),
                                onPressed: _loadingMessage ? null : _generateMorningMessage,
                              ),
                          ],
                        ),
                        if (_morningMessage != null) ...[
                          const SizedBox(height: 12),
                          Text(_morningMessage!, style: theme.textTheme.bodyMedium),
                          const SizedBox(height: 8),
                          Align(
                            alignment: Alignment.centerRight,
                            child: TextButton.icon(
                              icon: const Icon(Icons.refresh, size: 16),
                              label: const Text('重新生成'),
                              onPressed: _generateMorningMessage,
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(children: [
                          Icon(Icons.event, color: theme.colorScheme.primary),
                          const SizedBox(width: 8),
                          Text('今日日程', style: theme.textTheme.titleMedium),
                          const Spacer(),
                          Text('${data.todayEvents.length} 项', style: theme.textTheme.bodySmall),
                        ]),
                        const SizedBox(height: 8),
                        if (data.todayEvents.isEmpty)
                          Text('今天没有日程安排', style: theme.textTheme.bodySmall?.copyWith(color: theme.colorScheme.onSurfaceVariant))
                        else
                          ...data.todayEvents.take(5).map((e) => Padding(
                            padding: const EdgeInsets.symmetric(vertical: 4),
                            child: Row(children: [
                              const Icon(Icons.circle, size: 8),
                              const SizedBox(width: 8),
                              Expanded(child: Text(e['title'] ?? '', style: theme.textTheme.bodyMedium)),
                              Text(_formatTime(e), style: theme.textTheme.bodySmall),
                            ]),
                          )),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(children: [
                          Icon(Icons.checklist, color: theme.colorScheme.primary),
                          const SizedBox(width: 8),
                          Text('待办事项', style: theme.textTheme.titleMedium),
                          const Spacer(),
                          Text('${data.undoneTasks.length} 项未完成', style: theme.textTheme.bodySmall),
                        ]),
                        const SizedBox(height: 8),
                        if (data.undoneTasks.isEmpty)
                          Text('所有待办已完成 🎉', style: theme.textTheme.bodySmall?.copyWith(color: theme.colorScheme.onSurfaceVariant))
                        else
                          ...data.undoneTasks.take(5).map((t) => Padding(
                            padding: const EdgeInsets.symmetric(vertical: 4),
                            child: Row(children: [
                              Icon(Icons.circle_outlined, size: 8),
                              const SizedBox(width: 8),
                              Expanded(child: Text(t['title'] ?? '', style: theme.textTheme.bodyMedium)),
                              if (t['deadline'] != null)
                                Text(_formatDeadline(t['deadline'] as String), style: theme.textTheme.bodySmall),
                            ]),
                          )),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(children: [
                          Icon(Icons.flag, color: theme.colorScheme.primary),
                          const SizedBox(width: 8),
                          Text('长期目标', style: theme.textTheme.titleMedium),
                          const Spacer(),
                          Text('${data.goals.length} 个', style: theme.textTheme.bodySmall),
                        ]),
                        const SizedBox(height: 8),
                        if (data.goals.isEmpty)
                          Text('还没有设定目标', style: theme.textTheme.bodySmall?.copyWith(color: theme.colorScheme.onSurfaceVariant))
                        else
                          ...data.goals.take(3).map((g) => Padding(
                            padding: const EdgeInsets.symmetric(vertical: 4),
                            child: Row(children: [
                              const Icon(Icons.flag_outlined, size: 8),
                              const SizedBox(width: 8),
                              Expanded(child: Text(g['title'] ?? '', style: theme.textTheme.bodyMedium)),
                              Text('${g['progress_percent'] ?? 0}%', style: theme.textTheme.bodySmall),
                            ]),
                          )),
                      ],
                    ),
                  ),
                ),
              ],
            ),
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

  String _formatTime(Map<String, dynamic> event) {
    final start = event['start_time'] as String?;
    if (start == null) return '';
    try {
      return start.substring(11, 16);
    } catch (_) {
      return '';
    }
  }

  String _formatDeadline(String deadline) {
    try {
      return deadline.substring(0, 10);
    } catch (_) {
      return '';
    }
  }
}