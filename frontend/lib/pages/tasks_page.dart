import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/api_service.dart';
import '../providers/auth_provider.dart';

final _tasksProvider = FutureProvider.autoDispose<List<dynamic>>((ref) async {
  ref.watch(authProvider);
  final api = ref.read(apiServiceProvider);
  if (!api.hasToken) return [];
  try {
    return await api.getTasks();
  } catch (_) {
    return [];
  }
});

class TasksPage extends ConsumerWidget {
  const TasksPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final tasksAsync = ref.watch(_tasksProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('待办')),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _showAddDialog(context, ref),
        child: const Icon(Icons.add),
      ),
      body: tasksAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => _emptyView(theme),
        data: (tasks) {
          if (tasks.isEmpty) return _emptyView(theme);
          return RefreshIndicator(
            onRefresh: () async => ref.invalidate(_tasksProvider),
            child: ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: tasks.length,
              itemBuilder: (context, index) {
                final task = tasks[index] as Map<String, dynamic>;
                final isDone = task['status'] == 'done';

                return Card(
                  margin: const EdgeInsets.only(bottom: 8),
                  child: ListTile(
                    leading: Checkbox(
                      value: isDone,
                      onChanged: (v) async {
                        await ref.read(apiServiceProvider).updateTask(task['id'], {
                          'status': v == true ? 'done' : 'todo',
                        });
                        ref.invalidate(_tasksProvider);
                      },
                    ),
                    title: Text(
                      task['title'] ?? '',
                      style: TextStyle(
                        decoration: isDone ? TextDecoration.lineThrough : null,
                        color: isDone ? theme.colorScheme.onSurfaceVariant : null,
                      ),
                    ),
                    subtitle: Text(_taskSubtitle(task)),
                    trailing: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        _priorityChip(task['priority'] ?? 0),
                        IconButton(
                          icon: const Icon(Icons.delete_outline, size: 20),
                          onPressed: () async {
                            await ref.read(apiServiceProvider).deleteTask(task['id']);
                            ref.invalidate(_tasksProvider);
                          },
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
          );
        },
      ),
    );
  }

  Widget _emptyView(ThemeData theme) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.checklist, size: 80, color: theme.colorScheme.primary.withValues(alpha: 0.4)),
          const SizedBox(height: 16),
          Text('暂无待办', style: theme.textTheme.titleMedium),
          const SizedBox(height: 8),
          Text('点击右下角 + 添加', style: theme.textTheme.bodyMedium?.copyWith(color: theme.colorScheme.onSurfaceVariant)),
        ],
      ),
    );
  }

  Future<void> _showAddDialog(BuildContext context, WidgetRef ref) async {
    final titleCtrl = TextEditingController();
    final deadlineCtrl = TextEditingController();
    int priority = 0;

    await showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setState) => AlertDialog(
          title: const Text('添加待办'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(controller: titleCtrl, decoration: const InputDecoration(labelText: '标题', border: OutlineInputBorder())),
                const SizedBox(height: 12),
                TextField(controller: deadlineCtrl, decoration: const InputDecoration(labelText: '截止时间 (如: 2026-07-15T23:59:00)', border: OutlineInputBorder())),
                const SizedBox(height: 12),
                Row(
                  children: [
                    const Text('优先级: '),
                    for (int i = 0; i <= 3; i++)
                      ChoiceChip(
                        label: Text(['无', '低', '中', '高'][i]),
                        selected: priority == i,
                        onSelected: (v) => setState(() => priority = i),
                      ),
                  ],
                ),
              ],
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('取消')),
            FilledButton(
              onPressed: () async {
                if (titleCtrl.text.isEmpty) return;
                try {
                  await ref.read(apiServiceProvider).createTask({
                    'title': titleCtrl.text,
                    'priority': priority,
                    if (deadlineCtrl.text.isNotEmpty) 'deadline': deadlineCtrl.text,
                  });
                  if (ctx.mounted) Navigator.pop(ctx);
                  ref.invalidate(_tasksProvider);
                } catch (_) {
                  if (ctx.mounted) {
                    ScaffoldMessenger.of(ctx).showSnackBar(
                      const SnackBar(content: Text('添加失败，请检查网络连接')),
                    );
                  }
                }
              },
              child: const Text('添加'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _priorityChip(int priority) {
    final colors = [Colors.grey, Colors.green, Colors.orange, Colors.red];
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: colors[priority].withValues(alpha: 0.2),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(['无', '低', '中', '高'][priority], style: TextStyle(fontSize: 12, color: colors[priority])),
    );
  }

  String _taskSubtitle(Map<String, dynamic> task) {
    final deadline = task['deadline'] as String?;
    final status = task['status'] as String? ?? 'todo';
    final statusText = switch (status) {
      'todo' => '待办',
      'in_progress' => '进行中',
      'done' => '已完成',
      _ => status,
    };
    if (deadline != null) {
      return '截止: ${deadline.substring(0, 16).replaceAll("T", " ")} | $statusText';
    }
    return statusText;
  }
}