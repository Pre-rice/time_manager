import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
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
        onPressed: () => _showEditDialog(context, ref, null),
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
                      onPressed: () => _confirmDelete(context, ref, event),
                    ),
                    onTap: () => _showEditDialog(context, ref, event),
                  ),
                );
              },
            ),
          );
        },
      ),
    );
  }

  Future<void> _confirmDelete(BuildContext context, WidgetRef ref, Map<String, dynamic> event) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('删除日程'),
        content: Text('确定要删除"${event['title']}"吗？'),
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
      await ref.read(apiServiceProvider).deleteEvent(event['id']);
      ref.invalidate(_eventsProvider);
    }
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

  Future<void> _showEditDialog(BuildContext context, WidgetRef ref, Map<String, dynamic>? event) async {
    final isEdit = event != null;
    final titleCtrl = TextEditingController(text: event?['title'] ?? '');
    final descCtrl = TextEditingController(text: event?['description'] ?? '');
    DateTime startDate = DateTime.now();
    DateTime endDate = DateTime.now().add(const Duration(hours: 1));
    TimeOfDay startTime = TimeOfDay.fromDateTime(DateTime.now());
    TimeOfDay endTime = TimeOfDay.fromDateTime(DateTime.now().add(const Duration(hours: 1)));

    // 如果是编辑模式，从现有数据中解析时间
    if (isEdit) {
      final startStr = event!['start_time'] as String?;
      final endStr = event['end_time'] as String?;
      if (startStr != null && startStr.length >= 16) {
        try {
          startDate = DateTime.parse(startStr.substring(0, 16));
          startTime = TimeOfDay.fromDateTime(startDate);
        } catch (_) {}
      }
      if (endStr != null && endStr.length >= 16) {
        try {
          endDate = DateTime.parse(endStr.substring(0, 16));
          endTime = TimeOfDay.fromDateTime(endDate);
        } catch (_) {}
      }
    }

    final startDateStr = StateProvider<String>((ref) => DateFormat('yyyy-MM-dd').format(startDate));
    final endDateStr = StateProvider<String>((ref) => DateFormat('yyyy-MM-dd').format(endDate));

    await showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setState) {
          Future<void> pickDate(bool isStart) async {
            final initial = isStart ? startDate : endDate;
            final picked = await showDatePicker(
              context: ctx,
              initialDate: initial,
              firstDate: DateTime.now().subtract(const Duration(days: 30)),
              lastDate: DateTime.now().add(const Duration(days: 365)),
            );
            if (picked != null) {
              setState(() {
                if (isStart) startDate = picked;
                else endDate = picked;
              });
            }
          }

          Future<void> pickTime(bool isStart) async {
            final initial = isStart ? startTime : endTime;
            final picked = await showTimePicker(
              context: ctx,
              initialTime: initial,
            );
            if (picked != null) {
              setState(() {
                if (isStart) startTime = picked;
                else endTime = picked;
              });
            }
          }

          return AlertDialog(
            title: Text(isEdit ? '编辑日程' : '添加日程'),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  TextField(controller: titleCtrl, decoration: const InputDecoration(labelText: '标题', border: OutlineInputBorder())),
                  const SizedBox(height: 12),
                  TextField(controller: descCtrl, decoration: const InputDecoration(labelText: '描述', border: OutlineInputBorder()), maxLines: 2),
                  const SizedBox(height: 12),
                  InkWell(
                    onTap: () => pickDate(true),
                    child: InputDecorator(
                      decoration: const InputDecoration(labelText: '开始日期', border: OutlineInputBorder()),
                      child: Text(DateFormat('yyyy-MM-dd').format(startDate)),
                    ),
                  ),
                  const SizedBox(height: 8),
                  InkWell(
                    onTap: () => pickTime(true),
                    child: InputDecorator(
                      decoration: const InputDecoration(labelText: '开始时间', border: OutlineInputBorder()),
                      child: Text(startTime.format(ctx)),
                    ),
                  ),
                  const SizedBox(height: 12),
                  InkWell(
                    onTap: () => pickDate(false),
                    child: InputDecorator(
                      decoration: const InputDecoration(labelText: '结束日期', border: OutlineInputBorder()),
                      child: Text(DateFormat('yyyy-MM-dd').format(endDate)),
                    ),
                  ),
                  const SizedBox(height: 8),
                  InkWell(
                    onTap: () => pickTime(false),
                    child: InputDecorator(
                      decoration: const InputDecoration(labelText: '结束时间', border: OutlineInputBorder()),
                      child: Text(endTime.format(ctx)),
                    ),
                  ),
                ],
              ),
            ),
            actions: [
              TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('取消')),
              FilledButton(
                onPressed: () async {
                  if (titleCtrl.text.isEmpty) return;
                  final finalStart = DateTime(startDate.year, startDate.month, startDate.day, startTime.hour, startTime.minute);
                  final finalEnd = DateTime(endDate.year, endDate.month, endDate.day, endTime.hour, endTime.minute);
                  try {
                    final api = ref.read(apiServiceProvider);
                    if (isEdit) {
                      await api.updateEvent(event!['id'], {
                        'title': titleCtrl.text,
                        'description': descCtrl.text,
                        'start_time': finalStart.toIso8601String(),
                        'end_time': finalEnd.toIso8601String(),
                      });
                    } else {
                      await api.createEvent({
                        'title': titleCtrl.text,
                        'description': descCtrl.text,
                        'start_time': finalStart.toIso8601String(),
                        'end_time': finalEnd.toIso8601String(),
                      });
                    }
                    if (ctx.mounted) Navigator.pop(ctx);
                    ref.invalidate(_eventsProvider);
                  } catch (_) {
                    if (ctx.mounted) {
                      ScaffoldMessenger.of(ctx).showSnackBar(
                        const SnackBar(content: Text('操作失败，请检查网络连接')),
                      );
                    }
                  }
                },
                child: Text(isEdit ? '保存' : '添加'),
              ),
            ],
          );
        },
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
    try {
      final s = start!.substring(0, 16).replaceAll('T', ' ');
      if (end != null) {
        final e = end.substring(0, 16).replaceAll('T', ' ');
        return '$s ~ $e';
      }
      return s;
    } catch (_) {
      return start ?? '';
    }
  }
}