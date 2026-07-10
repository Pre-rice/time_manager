import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:table_calendar/table_calendar.dart';
import 'package:rrule/rrule.dart';
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

/// 准备时段数据类
class _PrepSlot {
  DateTime startTime;
  DateTime endTime;
  _PrepSlot({required this.startTime, required this.endTime});
}

/// 可复用的日程编辑弹窗（支持所有字段）
Future<Map<String, dynamic>?> showEventEditDialog(
  BuildContext context,
  Map<String, dynamic>? event, {
  List<dynamic> allEvents = const [],
}) async {
  final isEdit = event != null;
  final titleCtrl = TextEditingController(text: event?['title'] ?? '');
  final descCtrl = TextEditingController(text: event?['description'] ?? '');
  DateTime startDate = DateTime.now();
  DateTime endDate = DateTime.now().add(const Duration(hours: 1));
  TimeOfDay startTime = TimeOfDay.fromDateTime(DateTime.now());
  TimeOfDay endTime = TimeOfDay.fromDateTime(DateTime.now().add(const Duration(hours: 1)));
  String eventType = (event?['event_type'] as String?) ?? 'event';
  bool isAllDay = (event?['is_all_day'] as bool?) ?? false;

  // RRULE 状态：none | daily | weekly | weekly_byday | monthly | monthly_byday | yearly
  String repeatType = 'none';
  int repeatInterval = 1;
  int repeatCount = 0;
  // BYDAY：选中的星期几，1=周一 ... 7=周日
  Set<int> byDays = {};
  // BYMONTHDAY
  int byMonthDay = 1;

  // 准备时段列表
  final prepSlots = <_PrepSlot>[];

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

    final existingRrule = event['rrule'] as String?;
    if (existingRrule != null && existingRrule.isNotEmpty) {
      final hasByDay = RegExp(r'BYDAY=').hasMatch(existingRrule);
      final hasByMonthDay = RegExp(r'BYMONTHDAY=').hasMatch(existingRrule);
      if (existingRrule.contains('FREQ=DAILY')) repeatType = 'daily';
      else if (existingRrule.contains('FREQ=WEEKLY') && hasByDay) repeatType = 'weekly_byday';
      else if (existingRrule.contains('FREQ=WEEKLY')) repeatType = 'weekly';
      else if (existingRrule.contains('FREQ=MONTHLY') && hasByMonthDay) repeatType = 'monthly_byday';
      else if (existingRrule.contains('FREQ=MONTHLY')) repeatType = 'monthly';
      else if (existingRrule.contains('FREQ=YEARLY')) repeatType = 'yearly';
      final intervalMatch = RegExp(r'INTERVAL=(\d+)').firstMatch(existingRrule);
      if (intervalMatch != null) repeatInterval = int.parse(intervalMatch.group(1)!);
      final countMatch = RegExp(r'COUNT=(\d+)').firstMatch(existingRrule);
      if (countMatch != null) repeatCount = int.parse(countMatch.group(1)!);
      // 解析 BYDAY
      final byDayMatch = RegExp(r'BYDAY=([A-Z,]+)').firstMatch(existingRrule);
      if (byDayMatch != null) {
        final dayMap = {'MO': 1, 'TU': 2, 'WE': 3, 'TH': 4, 'FR': 5, 'SA': 6, 'SU': 7};
        for (final d in byDayMatch.group(1)!.split(',')) {
          final num = dayMap[d.trim()];
          if (num != null) byDays.add(num);
        }
      }
      final byMonthDayMatch = RegExp(r'BYMONTHDAY=(\d+)').firstMatch(existingRrule);
      if (byMonthDayMatch != null) byMonthDay = int.parse(byMonthDayMatch.group(1)!);
    }

    // 编辑时回填已有准备时段
    if (event['id'] != null) {
      final eventId = event['id'].toString();
      for (final e in allEvents) {
        final m = e as Map;
        if (m['is_preparation'] == true && m['parent_event_id']?.toString() == eventId) {
          final s = m['start_time'] as String?;
          final end = m['end_time'] as String?;
          if (s != null && end != null) {
            try {
              prepSlots.add(_PrepSlot(
                startTime: DateTime.parse(s),
                endTime: DateTime.parse(end),
              ));
            } catch (_) {}
          }
        }
      }
    }
  }

  return showDialog<Map<String, dynamic>>(
    context: context,
    builder: (ctx) => StatefulBuilder(
      builder: (ctx, setState) {
        // 准备时段日期/时间选择
        Future<void> pickPrepSlotTime(int index, bool isStart) async {
          final slot = prepSlots[index];
          final initial = isStart ? slot.startTime : slot.endTime;
          final date = await showDatePicker(
            context: ctx,
            initialDate: initial,
            firstDate: DateTime.now().subtract(const Duration(days: 30)),
            lastDate: DateTime.now().add(const Duration(days: 365)),
          );
          if (date == null) return;
          final time = await showTimePicker(
            context: ctx,
            initialTime: TimeOfDay.fromDateTime(initial),
          );
          if (time == null) return;
          final dt = DateTime(date.year, date.month, date.day, time.hour, time.minute);
          setState(() {
            if (isStart) prepSlots[index].startTime = dt;
            else prepSlots[index].endTime = dt;
          });
        }

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
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                TextField(
                  controller: titleCtrl,
                  decoration: const InputDecoration(labelText: '标题', border: OutlineInputBorder()),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: descCtrl,
                  decoration: const InputDecoration(labelText: '描述', border: OutlineInputBorder()),
                  maxLines: 2,
                ),
                const SizedBox(height: 12),
                // 日程类型
                DropdownButtonFormField<String>(
                  value: eventType,
                  decoration: const InputDecoration(labelText: '类型', border: OutlineInputBorder()),
                  items: const [
                    DropdownMenuItem(value: 'event', child: Text('日程')),
                    DropdownMenuItem(value: 'class', child: Text('课程')),
                    DropdownMenuItem(value: 'exam', child: Text('考试')),
                  ],
                  onChanged: (v) {
                    if (v != null) setState(() => eventType = v);
                  },
                ),
                const SizedBox(height: 12),
                // 开始日期
                InkWell(
                  onTap: () => pickDate(true),
                  child: InputDecorator(
                    decoration: const InputDecoration(labelText: '开始日期', border: OutlineInputBorder()),
                    child: Text(DateFormat('yyyy-MM-dd').format(startDate)),
                  ),
                ),
                const SizedBox(height: 8),
                if (!isAllDay)
                  InkWell(
                    onTap: () => pickTime(true),
                    child: InputDecorator(
                      decoration: const InputDecoration(labelText: '开始时间', border: OutlineInputBorder()),
                      child: Text(startTime.format(ctx)),
                    ),
                  ),
                if (!isAllDay) const SizedBox(height: 12),
                // 结束日期
                InkWell(
                  onTap: () => pickDate(false),
                  child: InputDecorator(
                    decoration: const InputDecoration(labelText: '结束日期', border: OutlineInputBorder()),
                    child: Text(DateFormat('yyyy-MM-dd').format(endDate)),
                  ),
                ),
                const SizedBox(height: 8),
                if (!isAllDay)
                  InkWell(
                    onTap: () => pickTime(false),
                    child: InputDecorator(
                      decoration: const InputDecoration(labelText: '结束时间', border: OutlineInputBorder()),
                      child: Text(endTime.format(ctx)),
                    ),
                  ),
                if (!isAllDay) const SizedBox(height: 12),
                // 全天开关
                SwitchListTile(
                  title: const Text('全天'),
                  value: isAllDay,
                  onChanged: (v) => setState(() => isAllDay = v),
                ),
                const Divider(),
                // ===== 重复设置 =====
                const Text('重复设置', style: TextStyle(fontWeight: FontWeight.bold)),
                const SizedBox(height: 8),
                DropdownButtonFormField<String>(
                  value: repeatType,
                  decoration: const InputDecoration(labelText: '重复类型', border: OutlineInputBorder()),
                  items: const [
                    DropdownMenuItem(value: 'none', child: Text('不重复')),
                    DropdownMenuItem(value: 'daily', child: Text('每天')),
                    DropdownMenuItem(value: 'weekly', child: Text('每周')),
                    DropdownMenuItem(value: 'weekly_byday', child: Text('每周指定日')),
                    DropdownMenuItem(value: 'monthly', child: Text('每月')),
                    DropdownMenuItem(value: 'monthly_byday', child: Text('每月指定日')),
                    DropdownMenuItem(value: 'yearly', child: Text('每年')),
                  ],
                  onChanged: (v) {
                    if (v != null) setState(() => repeatType = v);
                  },
                ),
                if (repeatType == 'weekly_byday') ...[
                  const SizedBox(height: 8),
                  const Text('选择每周重复日：', style: TextStyle(fontSize: 13)),
                  const SizedBox(height: 4),
                  Wrap(
                    spacing: 4,
                    children: List.generate(7, (i) {
                      final dayNum = i + 1; // 1=周一 ... 7=周日
                      final labels = ['一', '二', '三', '四', '五', '六', '日'];
                      final selected = byDays.contains(dayNum);
                      return FilterChip(
                        label: Text(labels[i], style: TextStyle(fontSize: 13, color: selected ? Colors.white : null)),
                        selected: selected,
                        onSelected: (v) {
                          setState(() {
                            if (v) byDays.add(dayNum);
                            else byDays.remove(dayNum);
                          });
                        },
                        selectedColor: Theme.of(ctx).colorScheme.primary,
                        checkmarkColor: Colors.white,
                        visualDensity: VisualDensity.compact,
                      );
                    }),
                  ),
                ],
                if (repeatType == 'monthly_byday') ...[
                  const SizedBox(height: 8),
                  TextField(
                    decoration: const InputDecoration(labelText: '每月几号（1-31）', hintText: '15', border: OutlineInputBorder()),
                    keyboardType: TextInputType.number,
                    controller: TextEditingController(text: byMonthDay.toString()),
                    onChanged: (v) {
                      final parsed = int.tryParse(v);
                      if (parsed != null && parsed >= 1 && parsed <= 31) byMonthDay = parsed;
                    },
                  ),
                ],
                if (repeatType != 'none') ...[
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          decoration: const InputDecoration(labelText: '间隔', hintText: '1', border: OutlineInputBorder()),
                          keyboardType: TextInputType.number,
                          controller: TextEditingController(text: repeatInterval.toString()),
                          onChanged: (v) {
                            final parsed = int.tryParse(v);
                            if (parsed != null && parsed > 0) repeatInterval = parsed;
                          },
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: TextField(
                          decoration: const InputDecoration(labelText: '重复次数（0=无限）', hintText: '0', border: OutlineInputBorder()),
                          keyboardType: TextInputType.number,
                          controller: TextEditingController(text: repeatCount.toString()),
                          onChanged: (v) {
                            final parsed = int.tryParse(v);
                            if (parsed != null) repeatCount = parsed;
                          },
                        ),
                      ),
                    ],
                  ),
                ],
                const Divider(),
                // ===== 准备时段 =====
                Row(
                  children: [
                    const Text('准备时段', style: TextStyle(fontWeight: FontWeight.bold)),
                    const Spacer(),
                    TextButton.icon(
                      icon: const Icon(Icons.add, size: 18),
                      label: const Text('添加'),
                      onPressed: () {
                        setState(() {
                          prepSlots.add(_PrepSlot(
                            startTime: startDate.add(const Duration(hours: 8)),
                            endTime: startDate.add(const Duration(hours: 9)),
                          ));
                        });
                      },
                    ),
                  ],
                ),
                if (prepSlots.isEmpty)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Text('暂无准备时段', style: TextStyle(color: Theme.of(ctx).colorScheme.onSurfaceVariant, fontSize: 13)),
                  ),
                ...prepSlots.asMap().entries.map((entry) {
                  final i = entry.key;
                  final slot = entry.value;
                  return Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Row(
                      children: [
                        Expanded(
                          child: InkWell(
                            onTap: () => pickPrepSlotTime(i, true),
                            child: InputDecorator(
                              decoration: const InputDecoration(
                                labelText: '开始',
                                border: OutlineInputBorder(),
                                contentPadding: EdgeInsets.symmetric(horizontal: 8, vertical: 8),
                              ),
                              child: Text(DateFormat('MM-dd HH:mm').format(slot.startTime), style: const TextStyle(fontSize: 13)),
                            ),
                          ),
                        ),
                        const Padding(
                          padding: EdgeInsets.symmetric(horizontal: 4),
                          child: Text('~', style: TextStyle(fontSize: 16)),
                        ),
                        Expanded(
                          child: InkWell(
                            onTap: () => pickPrepSlotTime(i, false),
                            child: InputDecorator(
                              decoration: const InputDecoration(
                                labelText: '结束',
                                border: OutlineInputBorder(),
                                contentPadding: EdgeInsets.symmetric(horizontal: 8, vertical: 8),
                              ),
                              child: Text(DateFormat('MM-dd HH:mm').format(slot.endTime), style: const TextStyle(fontSize: 13)),
                            ),
                          ),
                        ),
                        IconButton(
                          icon: const Icon(Icons.remove_circle_outline, color: Colors.red, size: 20),
                          onPressed: () => setState(() => prepSlots.removeAt(i)),
                          visualDensity: VisualDensity.compact,
                        ),
                      ],
                    ),
                  );
                }),
              ],
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('取消')),
            FilledButton(
              onPressed: () {
                if (titleCtrl.text.isEmpty) return;
                final data = <String, dynamic>{
                  'title': titleCtrl.text,
                  'description': descCtrl.text,
                  'event_type': eventType,
                  'is_all_day': isAllDay,
                  'type': 'event',
                };
                if (!isAllDay) {
                  final finalStart = DateTime(startDate.year, startDate.month, startDate.day, startTime.hour, startTime.minute);
                  final finalEnd = DateTime(endDate.year, endDate.month, endDate.day, endTime.hour, endTime.minute);
                  data['start_time'] = finalStart.toIso8601String();
                  data['end_time'] = finalEnd.toIso8601String();
                }
                // RRULE
                if (repeatType != 'none') {
                  final freqMap = {
                    'daily': 'DAILY',
                    'weekly': 'WEEKLY',
                    'weekly_byday': 'WEEKLY',
                    'monthly': 'MONTHLY',
                    'monthly_byday': 'MONTHLY',
                    'yearly': 'YEARLY',
                  };
                  String rrule = 'FREQ=${freqMap[repeatType]};INTERVAL=$repeatInterval';
                  if (repeatCount > 0) rrule += ';COUNT=$repeatCount';
                  if (repeatType == 'weekly_byday' && byDays.isNotEmpty) {
                    final dayCodes = {1: 'MO', 2: 'TU', 3: 'WE', 4: 'TH', 5: 'FR', 6: 'SA', 7: 'SU'};
                    final sorted = byDays.toList()..sort();
                    rrule += ';BYDAY=${sorted.map((d) => dayCodes[d]!).join(',')}';
                  } else if (repeatType == 'monthly_byday') {
                    rrule += ';BYMONTHDAY=$byMonthDay';
                  }
                  data['rrule'] = rrule;
                }
                // 准备时段
                if (prepSlots.isNotEmpty) {
                  data['preparation_slots'] = prepSlots
                      .where((s) => s.startTime.isBefore(s.endTime))
                      .map((s) => {
                        'start_time': s.startTime.toIso8601String(),
                        'end_time': s.endTime.toIso8601String(),
                      })
                      .toList();
                }
                Navigator.pop(ctx, data);
              },
              child: Text(isEdit ? '保存' : '添加'),
            ),
          ],
        );
      },
    ),
  );
}

/// 可复用的待办编辑弹窗（支持所有字段）
Future<Map<String, dynamic>?> showTaskEditDialog(
  BuildContext context,
  Map<String, dynamic>? task,
) async {
  final isEdit = task != null;
  final titleCtrl = TextEditingController(text: task?['title'] ?? '');
  final descCtrl = TextEditingController(text: task?['description'] ?? '');
  DateTime deadlineDate = DateTime.now().add(const Duration(days: 1));
  TimeOfDay deadlineTime = const TimeOfDay(hour: 23, minute: 59);
  bool isImportant = (task?['is_important'] as bool?) ?? false;
  String status = (task?['status'] as String?) ?? 'todo';
  final prepMinutesCtrl = TextEditingController(
    text: (task?['preparation_minutes'] as int?)?.toString() ?? '',
  );

  if (isEdit) {
    final deadlineStr = task['deadline'] as String?;
    if (deadlineStr != null && deadlineStr.length >= 16) {
      try {
        deadlineDate = DateTime.parse(deadlineStr.substring(0, 16));
        deadlineTime = TimeOfDay.fromDateTime(deadlineDate);
      } catch (_) {}
    }
    isImportant = (task['is_important'] as bool?) ?? false;
    status = (task['status'] as String?) ?? 'todo';
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
                TextField(
                  controller: titleCtrl,
                  decoration: const InputDecoration(labelText: '标题', border: OutlineInputBorder()),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: descCtrl,
                  decoration: const InputDecoration(labelText: '描述', border: OutlineInputBorder()),
                  maxLines: 2,
                ),
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
                SwitchListTile(
                  title: const Text('重要'),
                  value: isImportant,
                  onChanged: (v) => setState(() => isImportant = v),
                  secondary: Icon(isImportant ? Icons.star : Icons.star_border, color: isImportant ? Colors.amber : null),
                ),
                const SizedBox(height: 8),
                DropdownButtonFormField<String>(
                  value: status,
                  decoration: const InputDecoration(labelText: '状态', border: OutlineInputBorder()),
                  items: const [
                    DropdownMenuItem(value: 'todo', child: Text('待办')),
                    DropdownMenuItem(value: 'in_progress', child: Text('进行中')),
                    DropdownMenuItem(value: 'done', child: Text('已完成')),
                    DropdownMenuItem(value: 'cancelled', child: Text('已取消')),
                  ],
                  onChanged: (v) {
                    if (v != null) setState(() => status = v);
                  },
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: prepMinutesCtrl,
                  decoration: const InputDecoration(
                    labelText: '准备时间（分钟）',
                    hintText: '如：30',
                    border: OutlineInputBorder(),
                  ),
                  keyboardType: TextInputType.number,
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
                final data = <String, dynamic>{
                  'title': titleCtrl.text,
                  'description': descCtrl.text,
                  'deadline': finalDeadline.toIso8601String(),
                  'is_important': isImportant,
                  'status': status,
                  'type': 'task',
                };
                final prepMin = int.tryParse(prepMinutesCtrl.text);
                if (prepMin != null && prepMin > 0) {
                  data['preparation_minutes'] = prepMin;
                }
                Navigator.pop(ctx, data);
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

  /// 获取当月所有日程（含 RRULE 展开），按日期分组
  Map<DateTime, List<Map<String, dynamic>>> _buildEventMap(List<dynamic> events, DateTime monthStart, DateTime monthEnd) {
    final map = <DateTime, List<Map<String, dynamic>>>{};

    for (final e in events) {
      final event = Map<String, dynamic>.from(e as Map);
      final rruleStr = event['rrule'] as String?;
      final startStr = event['start_time'] as String?;
      if (startStr == null) continue;

      DateTime? startTimeParsed;
      try {
        startTimeParsed = DateTime.parse(startStr);
      } catch (_) {
        continue;
      }

      if (rruleStr == null || rruleStr.isEmpty) {
        // 非重复事件
        final key = DateTime(startTimeParsed.year, startTimeParsed.month, startTimeParsed.day);
        map.putIfAbsent(key, () => []);
        map[key]!.add(event);
        continue;
      }

      // 用 rrule 包解析完整的 rrule 字符串
      try {
        final rrule = RecurrenceRule.fromString(rruleStr);
        final occurrences = rrule.getAllInstances(
          start: startTimeParsed,
          after: monthStart.subtract(const Duration(days: 1)),
          before: monthEnd.add(const Duration(days: 1)),
          includeAfter: true,
          includeBefore: true,
        );
        final duration = event['end_time'] != null
            ? DateTime.parse(event['end_time']).difference(startTimeParsed)
            : const Duration(hours: 1);

        for (final occ in occurrences) {
          final ev = Map<String, dynamic>.from(event);
          ev['start_time'] = occ.toIso8601String();
          ev['end_time'] = occ.add(duration).toIso8601String();
          final key = DateTime(occ.year, occ.month, occ.day);
          map.putIfAbsent(key, () => []);
          map[key]!.add(ev);
        }
      } catch (_) {
        // 解析失败直接使用原始事件
        final key = DateTime(startTimeParsed.year, startTimeParsed.month, startTimeParsed.day);
        map.putIfAbsent(key, () => []);
        map[key]!.add(event);
      }
    }

    // 按时间排序
    for (final list in map.values) {
      list.sort((a, b) {
        final aStart = (a['start_time'] as String?) ?? '';
        final bStart = (b['start_time'] as String?) ?? '';
        return aStart.compareTo(bStart);
      });
    }

    return map;
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
    // 获取所有事件（用于编辑时回显准备时段）
    final allEvents = ref.read(_eventsProvider).asData?.value ?? [];
    final result = await showEventEditDialog(context, event, allEvents: allEvents);
    if (result == null) return;
    try {
      final api = ref.read(apiServiceProvider);
      if (event != null) {
        await api.updateEvent(event['id'], {
          'title': result['title'],
          'description': result['description'],
          'event_type': result['event_type'],
          'is_all_day': result['is_all_day'],
          if (result['start_time'] != null) 'start_time': result['start_time'],
          if (result['end_time'] != null) 'end_time': result['end_time'],
          if (result['rrule'] != null) 'rrule': result['rrule'],
          if (result['preparation_slots'] != null) 'preparation_slots': result['preparation_slots'],
        });
      } else {
        await api.createEvent({
          'title': result['title'],
          'description': result['description'],
          'event_type': result['event_type'],
          'is_all_day': result['is_all_day'],
          if (result['start_time'] != null) 'start_time': result['start_time'],
          if (result['end_time'] != null) 'end_time': result['end_time'],
          if (result['rrule'] != null) 'rrule': result['rrule'],
          if (result['preparation_slots'] != null) 'preparation_slots': result['preparation_slots'],
        });
      }
      ref.invalidate(_eventsProvider);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('操作失败: $e')),
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

          // 一次性计算当前聚焦月的所有日程
          final monthStart = DateTime(_focusedDay.year, _focusedDay.month, 1);
          final monthEnd = DateTime(_focusedDay.year, _focusedDay.month + 1, 0, 23, 59, 59);
          final eventMap = _buildEventMap(events, monthStart, monthEnd);
          final dayEvents = eventMap[DateTime(_selectedDay.year, _selectedDay.month, _selectedDay.day)] ?? [];

          return Column(
            children: [
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
                    return eventMap[DateTime(day.year, day.month, day.day)] ?? [];
                  },
                  headerStyle: const HeaderStyle(formatButtonVisible: false, titleCentered: true),
                  calendarStyle: CalendarStyle(
                    todayDecoration: BoxDecoration(
                      color: theme.colorScheme.primary.withValues(alpha: 0.5),
                      shape: BoxShape.circle,
                    ),
                    selectedDecoration: BoxDecoration(
                      color: theme.colorScheme.primary,
                      shape: BoxShape.circle,
                    ),
                  ),
                  calendarBuilders: CalendarBuilders(
                    markerBuilder: (context, date, events) {
                      if (events.isEmpty) return null;
                      final colors = <Color>{
                        for (final e in events)
                          _eventColor((e as Map)['event_type'] as String? ?? 'event')
                      };
                      return Row(
                        mainAxisSize: MainAxisSize.min,
                        children: colors.take(3).map((color) {
                          return Container(
                            width: 6,
                            height: 6,
                            margin: const EdgeInsets.symmetric(horizontal: 1),
                            decoration: BoxDecoration(
                              color: color,
                              shape: BoxShape.circle,
                            ),
                          );
                        }).toList(),
                      );
                    },
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
                        child: Text('当天无日程', style: theme.textTheme.bodyMedium?.copyWith(color: theme.colorScheme.onSurfaceVariant)),
                      )
                    : RefreshIndicator(
                        onRefresh: () async => ref.invalidate(_eventsProvider),
                        child: ListView.builder(
                          padding: const EdgeInsets.fromLTRB(16, 4, 16, 80),
                          itemCount: dayEvents.length,
                          itemBuilder: (context, index) {
                            final event = dayEvents[index];
                            final hasRrule = (event['rrule'] as String?)?.isNotEmpty ?? false;
                            final isPrep = event['is_preparation'] as bool? ?? false;
                            return Card(
                              margin: const EdgeInsets.only(bottom: 8),
                              child: ListTile(
                                leading: CircleAvatar(
                                  backgroundColor: _eventColor(event['event_type'] ?? 'event'),
                                  child: Icon(_eventIcon(event['event_type'] ?? 'event'), color: Colors.white),
                                ),
                                title: Row(
                                  children: [
                                    if (isPrep)
                                      const Padding(
                                        padding: EdgeInsets.only(right: 4),
                                        child: Icon(Icons.pending, size: 16, color: Colors.orange),
                                      ),
                                    Flexible(child: Text(event['title'] ?? '', overflow: TextOverflow.ellipsis)),
                                    if (hasRrule)
                                      const Padding(
                                        padding: EdgeInsets.only(left: 4),
                                        child: Icon(Icons.repeat, size: 16, color: Colors.grey),
                                      ),
                                  ],
                                ),
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