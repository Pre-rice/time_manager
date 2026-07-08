import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/api_service.dart';
import '../providers/auth_provider.dart';

final _goalsProvider = FutureProvider.autoDispose<List<dynamic>>((ref) async {
  final api = ref.read(apiServiceProvider);
  return api.getGoals();
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
        onPressed: () => _showAddDialog(context, ref),
        child: const Icon(Icons.add),
      ),
      body: goalsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('加载失败: $e')),
        data: (goals) {
          if (goals.isEmpty) {
            return Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.flag, size: 80, color: theme.colorScheme.primary.withValues(alpha: 0.4)),
                  const SizedBox(height: 16),
                  Text('暂无目标', style: theme.textTheme.titleMedium?.copyWith(color: theme.colorScheme.onSurfaceVariant)),
                  Text('点击右下角 + 添加', style: theme.textTheme.bodyMedium?.copyWith(color: theme.colorScheme.onSurfaceVariant)),
                ],
              ),
            );
          }
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
                            Expanded(
                              child: Text(goal['title'] ?? '', style: theme.textTheme.titleMedium),
                            ),
                            IconButton(
                              icon: const Icon(Icons.delete_outline, size: 20),
                              onPressed: () async {
                                await ref.read(apiServiceProvider).deleteGoal(goal['id']);
                                ref.invalidate(_goalsProvider);
                              },
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
                        SizedBox(
                          width: double.infinity,
                          child: OutlinedButton.icon(
                            icon: const Icon(Icons.update, size: 16),
                            label: const Text('更新进度'),
                            onPressed: () => _showProgressDialog(context, ref, goal),
                          ),
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

  Future<void> _showAddDialog(BuildContext context, WidgetRef ref) async {
    final titleCtrl = TextEditingController();
    final targetCtrl = TextEditingController();
    final unitCtrl = TextEditingController();

    await showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('添加目标'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(controller: titleCtrl, decoration: const InputDecoration(labelText: '目标名称', border: OutlineInputBorder())),
              const SizedBox(height: 12),
              TextField(controller: targetCtrl, decoration: const InputDecoration(labelText: '目标值 (可选)', border: OutlineInputBorder()), keyboardType: TextInputType.number),
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
              await ref.read(apiServiceProvider).createGoal({
                'title': titleCtrl.text,
                if (targetCtrl.text.isNotEmpty) 'target_value': double.parse(targetCtrl.text),
                if (unitCtrl.text.isNotEmpty) 'unit': unitCtrl.text,
              });
              if (ctx.mounted) Navigator.pop(ctx);
              ref.invalidate(_goalsProvider);
            },
            child: const Text('添加'),
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
              await ref.read(apiServiceProvider).updateGoalProgress(goal['id'], double.parse(ctrl.text));
              if (ctx.mounted) Navigator.pop(ctx);
              ref.invalidate(_goalsProvider);
            },
            child: const Text('更新'),
          ),
        ],
      ),
    );
  }
}