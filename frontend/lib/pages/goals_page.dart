import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/auth_provider.dart';

final _goalsProvider = FutureProvider.autoDispose<List<dynamic>>((ref) async {
  ref.watch(authProvider);
  final api = ref.read(apiServiceProvider);
  if (!api.hasToken) return [];
  try {
    return await api.getGoals();
  } catch (_) {
    return [];
  }
});

class GoalsPage extends ConsumerWidget {
  const GoalsPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final goalsAsync = ref.watch(_goalsProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('长期目标')),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _showEditDialog(context, ref, null),
        child: const Icon(Icons.add),
      ),
      body: goalsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => _emptyView(theme),
        data: (goals) {
          if (goals.isEmpty) return _emptyView(theme);
          return RefreshIndicator(
            onRefresh: () async => ref.invalidate(_goalsProvider),
            child: ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: goals.length,
              itemBuilder: (context, index) {
                final goal = goals[index] as Map<String, dynamic>;
                final progress = goal['progress_percent'] ?? 0;
                final current = (goal['current_value'] as num?)?.toDouble() ?? 0;
                final target = (goal['target_value'] as num?)?.toDouble();

                return Card(
                  margin: const EdgeInsets.only(bottom: 12),
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Icon(Icons.flag, color: theme.colorScheme.primary),
                            const SizedBox(width: 8),
                            Expanded(child: Text(goal['title'] ?? '', style: theme.textTheme.titleMedium)),
                            IconButton(
                              icon: const Icon(Icons.delete_outline, size: 20),
                              onPressed: () => _confirmDelete(context, ref, goal),
                            ),
                          ],
                        ),
                        if (goal['description'] != null) ...[
                          const SizedBox(height: 4),
                          Text(goal['description'], style: theme.textTheme.bodySmall?.copyWith(color: theme.colorScheme.onSurfaceVariant)),
                        ],
                        const SizedBox(height: 12),
                        ClipRRect(
                          borderRadius: BorderRadius.circular(8),
                          child: LinearProgressIndicator(
                            value: progress / 100.0,
                            minHeight: 12,
                            backgroundColor: theme.colorScheme.surfaceContainerHighest,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text('$progress%', style: theme.textTheme.bodySmall?.copyWith(fontWeight: FontWeight.bold)),
                            Text(
                              target != null ? '$current / $target ${goal['unit'] ?? ''}' : '$current ${goal['unit'] ?? ''}',
                              style: theme.textTheme.bodySmall,
                            ),
                          ],
                        ),
                        const SizedBox(height: 8),
                        Row(
                          children: [
                            Expanded(
                              child: OutlinedButton.icon(
                                icon: const Icon(Icons.update, size: 16),
                                label: const Text('更新进度'),
                                onPressed: () => _showProgressDialog(context, ref, goal),
                              ),
                            ),
                            const SizedBox(width: 8),
                            Expanded(
                              child: OutlinedButton.icon(
                                icon: const Icon(Icons.edit, size: 16),
                                label: const Text('编辑'),
                                onPressed: () => _showEditDialog(context, ref, goal),
                              ),
                            ),
                          ],
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

  Future<void> _confirmDelete(BuildContext context, WidgetRef ref, Map<String, dynamic> goal) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('删除目标'),
        content: Text('确定要删除"${goal['title']}"吗？'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('取消')),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: Theme.of(context).colorScheme.error),
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('删除'),
          ),
        ],
      ),
    );
    if (ok == true) {
      await ref.read(apiServiceProvider).deleteGoal(goal['id']);
      ref.invalidate(_goalsProvider);
    }
  }

  Widget _emptyView(ThemeData theme) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.flag, size: 80, color: theme.colorScheme.primary.withValues(alpha: 0.4)),
          const SizedBox(height: 16),
          Text('暂无目标', style: theme.textTheme.titleMedium),
          const SizedBox(height: 8),
          Text('点击右下角 + 添加', style: theme.textTheme.bodyMedium?.copyWith(color: theme.colorScheme.onSurfaceVariant)),
        ],
      ),
    );
  }

  Future<void> _showEditDialog(BuildContext context, WidgetRef ref, Map<String, dynamic>? goal) async {
    final isEdit = goal != null;
    final titleCtrl = TextEditingController(text: goal?['title'] ?? '');
    final descCtrl = TextEditingController(text: goal?['description'] ?? '');
    final targetCtrl = TextEditingController(text: goal?['target_value']?.toString() ?? '');
    final unitCtrl = TextEditingController(text: goal?['unit'] ?? '');

    await showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(isEdit ? '编辑目标' : '添加目标'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(controller: titleCtrl, decoration: const InputDecoration(labelText: '目标名称', border: OutlineInputBorder())),
              const SizedBox(height: 12),
              TextField(controller: descCtrl, decoration: const InputDecoration(labelText: '描述', border: OutlineInputBorder()), maxLines: 2),
              const SizedBox(height: 12),
              TextField(controller: targetCtrl, decoration: const InputDecoration(labelText: '目标值', border: OutlineInputBorder()), keyboardType: TextInputType.number),
              const SizedBox(height: 12),
              TextField(controller: unitCtrl, decoration: const InputDecoration(labelText: '单位 (如: 公里/次/小时)', border: OutlineInputBorder())),
            ],
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('取消')),
          FilledButton(
            onPressed: () async {
              if (titleCtrl.text.isEmpty) return;
              try {
                final api = ref.read(apiServiceProvider);
                final data = <String, dynamic>{
                  'title': titleCtrl.text,
                  'description': descCtrl.text,
                  if (targetCtrl.text.isNotEmpty) 'target_value': double.parse(targetCtrl.text),
                  'unit': unitCtrl.text,
                };
                if (isEdit) {
                  if (targetCtrl.text.isNotEmpty) {
                    data['target_value'] = double.parse(targetCtrl.text);
                  }
                  await api.updateGoal(goal['id'], data);
                } else {
                  await api.createGoal(data);
                }
                if (ctx.mounted) Navigator.pop(ctx);
                ref.invalidate(_goalsProvider);
              } catch (_) {
                if (ctx.mounted) {
                  ScaffoldMessenger.of(ctx).showSnackBar(
                    const SnackBar(content: Text('操作失败，请检查输入')),
                  );
                }
              }
            },
            child: Text(isEdit ? '保存' : '添加'),
          ),
        ],
      ),
    );
  }

  Future<void> _showProgressDialog(BuildContext context, WidgetRef ref, Map<String, dynamic> goal) async {
    final ctrl = TextEditingController();

    await showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('更新进度: ${goal['title']}'),
        content: TextField(
          controller: ctrl,
          decoration: const InputDecoration(labelText: '当前值', border: OutlineInputBorder()),
          keyboardType: TextInputType.number,
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('取消')),
          FilledButton(
            onPressed: () async {
              if (ctrl.text.isEmpty) return;
              try {
                await ref.read(apiServiceProvider).updateGoalProgress(goal['id'], double.parse(ctrl.text));
                if (ctx.mounted) Navigator.pop(ctx);
                ref.invalidate(_goalsProvider);
              } catch (_) {
                if (ctx.mounted) {
                  ScaffoldMessenger.of(ctx).showSnackBar(
                    const SnackBar(content: Text('更新失败，请检查网络连接')),
                  );
                }
              }
            },
            child: const Text('更新'),
          ),
        ],
      ),
    );
  }
}