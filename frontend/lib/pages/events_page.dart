import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:table_calendar/table_calendar.dart';
import '../services/api_service.dart';
import '../providers/auth_provider.dart';
import '../providers/week_start_provider.dart';

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

/// 可复用的日程编辑弹窗
Future<Map<String, dynamic>?> showEventEditDialog(
  BuildContext context,
  Map<String, dynamic>? event,
) async {
  final isEdit = event != null;
  final titleCtrl = TextEditingController(text: event?['title'] ?? '');
  final descCtrl = TextEditingController(text: event?['description'] ?? '');
  DateTime startDate = DateTime.now();
  DateTime endDate = DateTime.now().add(const Duration(hours: 1));
  TimeOfDay startTime = TimeOfDay.fromDateTime(DateTime.now());
  TimeOfDay endTime = TimeOfDay.fromDateTime(DateTime.now().add(const Duration(hours: 1)));

  if (isEdit) {
    final startStr = event['start_time'] as String?;
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

  return showDialog<Map<String, dynamic>>(
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
              onPressed: () {
                if (titleCtrl.text.isEmpty) return;
                final finalStart = DateTime(startDate.year, startDate.month, startDate.day, startTime.hour, startTime.minute);
                final finalEnd = DateTime(endDate.year, endDate.month, endDate.day, endTime.hour, endTime.minute);
                Navigator.pop(ctx, {
                  'title': titleCtrl.text,
                  'description': descCtrl.text,
                  'start_time': finalStart.toIso8601String(),
                  'end_time': finalEnd.toIso8601String(),
                  'type': 'event',
                });
              },
              child: Text(isEdit ? '保存' : '添加'),
            ),
          ],
        );
      },
    ),
  );
}

/// 可复用的待办编辑弹窗
Future<Map<String, dynamic>?> showTaskEditDialog(
  BuildContext context,
  Map<String, dynamic>? task,
) async {
  final isEdit = task != null;
  final titleCtrl = TextEditingController(text: task?['title'] ?? '');
  final descCtrl = TextEditingController(text: task?['description'] ?? '');
  DateTime deadlineDate = DateTime.now().add(const Duration(days: 1));
  TimeOfDay deadlineTime = const TimeOfDay(hour: 23, minute: 59);
  int priority = (task?['priority'] as int?) ?? 1;

  if (isEdit) {
    final deadlineStr = task['deadline'] as String?;
    if (deadlineStr != null && deadlineStr.length >= 16) {
      try {
        deadlineDate = DateTime.parse(deadlineStr.substring(0, 16));
        deadlineTime = TimeOfDay.fromDateTime(deadlineDate);
      } catch (_) {}
    }
    priority = (task['priority'] as int?) ?? 1;
  }

  return showDialog<Map<String, dynamic>>(
    context: context,
    builder: (ctx) => StatefulBuilder(
      builder: (ctx, setState) {
        Future<void> pickDate() async {
          final picked = await showDatePicker(
            context: ctx,
            initialDate: deadlineDate,
            firstDate: DateTime.now().subtract(const Duration(days: 1)),
            lastDate: DateTime.now().add(const Duration(days: 365)),
          );
          if (picked != null) {
            setState(() => deadlineDate = picked);
          }
        }

        Future<void> pickTime() async {
          final picked = await showTimePicker(
            context: ctx,
            initialTime: deadlineTime,
          );
          if (picked != null) {
            setState(() => deadlineTime = picked);
          }
        }

        return AlertDialog(
          title: Text(isEdit ? '编辑待办' : '添加待办'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(controller: titleCtrl, decoration: const InputDecoration(labelText: '标题', border: OutlineInputBorder())),
                const SizedBox(height: 12),
                TextField(controller: descCtrl, decoration: const InputDecoration(labelText: '描述', border: OutlineInputBorder()), maxLines: 2),
                const SizedBox(height: 12),
                InkWell(
                  onTap: pickDate,
                  child: InputDecorator(
                    decoration: const InputDecoration(labelText: '截止日期', border: OutlineInputBorder()),
                    child: Text(DateFormat('yyyy-MM-dd').format(deadlineDate)),
                  ),
                ),
                const SizedBox(height: 8),
                InkWell(
                  onTap: pickTime,
                  child: InputDecorator(
                    decoration: const InputDecoration(labelText: '截止时间', border: OutlineInputBorder()),
                    child: Text(deadlineTime.format(ctx)),
                  ),
                ),
                const SizedBox(height: 12),
                DropdownButtonFormField<int>(
                  value: priority,
                  decoration: const InputDecoration(labelText: '优先级', border: OutlineInputBorder()),
                  items: const [
                    DropdownMenuItem(value: 0, child: Text('无')),
                    DropdownMenuItem(value: 1, child: Text('低')),
                    DropdownMenuItem(value: 2, child: Text('中')),
                    DropdownMenuItem(value: 3, child: Text('高')),
                  ],
                  onChanged: (v) {
                    if (v != null) setState(() => priority = v);
                  },
                ),
              ],
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('取消')),
            FilledButton(
              onPressed: () {
                if (titleCtrl.text.isEmpty) return;
                final finalDeadline = DateTime(deadlineDate.year, deadlineDate.month, deadlineDate.day, deadlineTime.hour, deadlineTime.minute);
                Navigator.pop(ctx, {
                  'title': titleCtrl.text,
                  'description': descCtrl.text,
                  'deadline': finalDeadline.toIso8601String(),
                  'priority': priority,
                  'type': 'task',
                });
              },
              child: Text(isEdit ? '保存' : '添加'),
            ),
          ],
        );
      },
    ),
  );
}

class EventsPage extends ConsumerStatefulWidget {
  const EventsPage({super.key});

  @override
  ConsumerState<EventsPage> createState() => _EventsPageState();
}

class _EventsPageState extends ConsumerState<EventsPage> {
  DateTime _selectedDay = DateTime.now();
  DateTime _focusedDay = DateTime.now();

  Map<DateTime, List<Map<String, dynamic>>> _groupEvents(List<dynamic> events) {
    final map = <DateTime, List<Map<String, dynamic>>>{};
    for (final e in events) {
      final event = Map<String, dynamic>.from(e as Map);
      final startStr = event['start_time'] as String?;
      if (startStr == null) continue;
      try {
        final date = DateTime.parse(startStr.substring(0, 10));
        final key = DateTime(date.year, date.month, date.day);
        map.putIfAbsent(key, () => []);
        map[key]!.add(event);
      } catch (_) {}
    }
    return map;
  }

  List<Map<String, dynamic>> _getEventsForDay(DateTime day, List<dynamic> events) {
    final result = <Map<String, dynamic>>[];
    for (final e in events) {
      final event = Map<String, dynamic>.from(e as Map);
      final startStr = event['start_time'] as String?;
      if (startStr == null) continue;
      try {
        final date = DateTime.parse(startStr.substring(0, 10));
        if (isSameDay(day, date)) {
          result.add(event);
        }
      } catch (_) {}
    }
    result.sort((a, b) {
      final aStart = a['start_time'] as String? ?? '';
      final bStart = b['start_time'] as String? ?? '';
      return aStart.compareTo(bStart);
    });
    return result;
  }

  Future<void> _confirmDelete(Map<String, dynamic> event) async {
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

  Future<void> _showEditDialog(Map<String, dynamic>? event) async {
    final result = await showEventEditDialog(context, event);
    if (result == null) return;
    try {
      final api = ref.read(apiServiceProvider);
      if (event != null) {
        await api.updateEvent(event['id'], {
          'title': result['title'],
          'description': result['description'],
          'start_time': result['start_time'],
          'end_time': result['end_time'],
        });
      } else {
        await api.createEvent({
          'title': result['title'],
          'description': result['description'],
          'start_time': result['start_time'],
          'end_time': result['end_time'],
        });
      }
      ref.invalidate(_eventsProvider);
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('操作失败，请检查网络连接')),
        );
      }
    }
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

  Widget _emptyView() {
    final theme = Theme.of(context);
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

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final eventsAsync = ref.watch(_eventsProvider);
    final weekStart = ref.watch(weekStartProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('日程')),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _showEditDialog(null),
        child: const Icon(Icons.add),
      ),
      body: eventsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (_, __) => _emptyView(),
        data: (events) {
          final weekDay = weekStart.isMonday ? StartingDayOfWeek.monday : StartingDayOfWeek.sunday;
          final groupedEvents = _groupEvents(events);
          final dayEvents = _getEventsForDay(_selectedDay, events);

          return Column(
            children: [
              // 月历 — 用 SizedBox 固定高度防止溢出
              SizedBox(
                height: 320,
                child: TableCalendar(
                  firstDay: DateTime.utc(2020, 1, 1),
                  lastDay: DateTime.utc(2030, 12, 31),
                  focusedDay: _focusedDay,
                  startingDayOfWeek: weekDay,
                  selectedDayPredicate: (day) => isSameDay(_selectedDay, day),
                  onDaySelected: (selectedDay, focusedDay) {
                    setState(() {
                      _selectedDay = selectedDay;
                      _focusedDay = focusedDay;
                    });
                  },
                  onPageChanged: (focusedDay) {
                    setState(() => _focusedDay = focusedDay);
                  },
                  eventLoader: (day) {
                    return groupedEvents[DateTime(day.year, day.month, day.day)] ?? [];
                  },
                  headerStyle: const HeaderStyle(
                    formatButtonVisible: false,
                    titleCentered: true,
                  ),
                  calendarStyle: CalendarStyle(
                    todayDecoration: BoxDecoration(
                      color: theme.colorScheme.primary.withValues(alpha: 0.5),
                      shape: BoxShape.circle,
                    ),
                    selectedDecoration: BoxDecoration(
                      color: theme.colorScheme.primary,
                      shape: BoxShape.circle,
                    ),
                    markerDecoration: BoxDecoration(
                      color: theme.colorScheme.secondary,
                      shape: BoxShape.circle,
                    ),
                  ),
                  locale: 'zh_CN',
                ),
              ),
              const Divider(height: 1),
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
                child: Row(
                  children: [
                    Text(
                      DateFormat('M月d日 EEEE', 'zh_CN').format(_selectedDay),
                      style: theme.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      '${dayEvents.length}个日程',
                      style: theme.textTheme.bodySmall?.copyWith(color: theme.colorScheme.onSurfaceVariant),
                    ),
                  ],
                ),
              ),
              Expanded(
                child: dayEvents.isEmpty
                    ? Center(
                        child: Text(
                          '当天无日程',
                          style: theme.textTheme.bodyMedium?.copyWith(color: theme.colorScheme.onSurfaceVariant),
                        ),
                      )
                    : RefreshIndicator(
                        onRefresh: () async => ref.invalidate(_eventsProvider),
                        child: ListView.builder(
                          padding: const EdgeInsets.fromLTRB(16, 4, 16, 80),
                          itemCount: dayEvents.length,
                          itemBuilder: (context, index) {
                            final event = dayEvents[index];
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
                                  onPressed: () => _confirmDelete(event),
                                ),
                                onTap: () => _showEditDialog(event),
                              ),
                            );
                          },
                        ),
                      ),
              ),
            ],
          );
        },
      ),
    );
  }
}