import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/api_service.dart';
import '../providers/auth_provider.dart';

final _eventsProvider = FutureProvider.autoDispose<List<dynamic>>((ref) async {
  ref.watch(authProvider);
  final api = ref.read(apiServiceProvider);
  if (!api.hasToken) return [];
  try {
    return await api.getEvents();
  } catch (_) {
    return [];
  }
});

class EventsPage extends ConsumerWidget {
  const EventsPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final eventsAsync = ref.watch(_eventsProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('日程')),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _showAddDialog(context, ref),
        child: const Icon(Icons.add),
      ),
      body: eventsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (_, __) => _emptyView(theme),
        data: (events) {
          if (events.isEmpty) return _emptyView(theme);
          return RefreshIndicator(
            onRefresh: () async => ref.invalidate(_eventsProvider),
            child: ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: events.length,
              itemBuilder: (context, index) {
                final event = events[index] as Map<String, dynamic>;
                return Card(
                  margin: const EdgeInsets.only(bottom: 8),
                  child: ListTile(
                    leading: CircleAvatar(
                      backgroundColor: _eventColor(event['event_type'] ?? 'event'),
                      child: Icon(_eventIcon(event['event_type'] ?? 'event'), color: Colors.white),
                    ),
                    title: Text(event['title'] ?? ''),
                    subtitle: Text(_formatTime(event)),
                    trailing: IconButton(
                      icon: const Icon(Icons.delete_outline),
                      onPressed: () async {
                        await ref.read(apiServiceProvider).deleteEvent(event['id']);
                        ref.invalidate(_eventsProvider);
                      },
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
          Icon(Icons.event, size: 80, color: theme.colorScheme.primary.withValues(alpha: 0.4)),
          const SizedBox(height: 16),
          Text('暂无日程', style: theme.textTheme.titleMedium),
          const SizedBox(height: 8),
          Text('点击右下角 + 添加', style: theme.textTheme.bodyMedium?.copyWith(color: theme.colorScheme.onSurfaceVariant)),
        ],
      ),
    );
  }

  Future<void> _showAddDialog(BuildContext context, WidgetRef ref) async {
    final titleCtrl = TextEditingController();
    final descCtrl = TextEditingController();
    final startDateCtrl = TextEditingController();
    final endDateCtrl = TextEditingController();

    await showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('添加日程'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(controller: titleCtrl, decoration: const InputDecoration(labelText: '标题', border: OutlineInputBorder())),
              const SizedBox(height: 12),
              TextField(controller: descCtrl, decoration: const InputDecoration(labelText: '描述', border: OutlineInputBorder()), maxLines: 2),
              const SizedBox(height: 12),
              TextField(controller: startDateCtrl, decoration: const InputDecoration(labelText: '开始时间 (如: 2026-07-10T09:00:00)', border: OutlineInputBorder())),
              const SizedBox(height: 12),
              TextField(controller: endDateCtrl, decoration: const InputDecoration(labelText: '结束时间 (如: 2026-07-10T10:30:00)', border: OutlineInputBorder())),
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
                await api.createEvent({
                  'title': titleCtrl.text,
                  'description': descCtrl.text,
                  if (startDateCtrl.text.isNotEmpty) 'start_time': startDateCtrl.text,
                  if (endDateCtrl.text.isNotEmpty) 'end_time': endDateCtrl.text,
                });
                if (ctx.mounted) Navigator.pop(ctx);
                ref.invalidate(_eventsProvider);
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
    );
  }

  Color _eventColor(String type) {
    switch (type) {
      case 'class': return Colors.blue;
      case 'exam': return Colors.red;
      default: return Colors.green;
    }
  }

  IconData _eventIcon(String type) {
    switch (type) {
      case 'class': return Icons.school;
      case 'exam': return Icons.assignment;
      default: return Icons.event;
    }
  }

  String _formatTime(Map<String, dynamic> event) {
    final start = event['start_time'] as String?;
    final end = event['end_time'] as String?;
    if (start == null && end == null) return '全天';
    final s = start?.substring(0, 16).replaceAll('T', ' ') ?? '';
    final e = end?.substring(0, 16).replaceAll('T', ' ') ?? '';
    return '$s ~ $e';
  }
}