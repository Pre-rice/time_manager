import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/api_service.dart';
import '../providers/auth_provider.dart';

class AiAssistantPage extends ConsumerStatefulWidget {
  const AiAssistantPage({super.key});

  @override
  ConsumerState<AiAssistantPage> createState() => _AiAssistantPageState();
}

class _AiAssistantPageState extends ConsumerState<AiAssistantPage> {
  final _textController = TextEditingController();
  List<Map<String, dynamic>> _results = [];
  bool _loading = false;

  @override
  void dispose() {
    _textController.dispose();
    super.dispose();
  }

  Future<void> _extract() async {
    if (_textController.text.trim().isEmpty) return;
    setState(() => _loading = true);
    try {
      final api = ref.read(apiServiceProvider);
      final items = await api.extractFromText(_textController.text.trim());
      // 叠加：追加到现有结果
      setState(() {
        for (final item in items) {
          if (item is Map) {
            _results.add(Map<String, dynamic>.from(item));
          }
        }
      });
    } catch (e) {
      String msg = 'AI 提取失败，请检查 AI 配置';
      if (e.toString().contains('请先在设置中配置 AI')) {
        msg = '请先在设置页面配置 API Key';
      }
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _addItem(Map<String, dynamic> item) async {
    try {
      final api = ref.read(apiServiceProvider);
      if (item['type'] == 'event') {
        final data = Map<String, dynamic>.from(item);
        data.remove('type');
        await api.createEvent(data);
      } else {
        final data = Map<String, dynamic>.from(item);
        data.remove('type');
        await api.createTask(data);
      }
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('已添加: ${item['title']}')),
        );
        setState(() => _results.remove(item));
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('添加失败')),
        );
      }
    }
  }

  Future<void> _editItem(int index) async {
    final item = _results[index];
    final isEvent = item['type'] == 'event';
    final titleCtrl = TextEditingController(text: item['title'] ?? '');
    final descCtrl = TextEditingController(text: item['description'] ?? '');
    final startCtrl = TextEditingController(text: item['start_time'] ?? '');
    final endCtrl = TextEditingController(text: item['end_time'] ?? '');
    final deadlineCtrl = TextEditingController(text: item['deadline'] ?? '');
    int priority = (item['priority'] as int?) ?? 0;

    final result = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setState) => AlertDialog(
          title: Text('编辑${isEvent ? "日程" : "待办"}'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(controller: titleCtrl, decoration: const InputDecoration(labelText: '标题', border: OutlineInputBorder())),
                const SizedBox(height: 8),
                TextField(controller: descCtrl, decoration: const InputDecoration(labelText: '描述', border: OutlineInputBorder()), maxLines: 2),
                const SizedBox(height: 8),
                if (isEvent) ...[
                  TextField(controller: startCtrl, decoration: const InputDecoration(labelText: '开始时间 (ISO)', border: OutlineInputBorder()), style: const TextStyle(fontSize: 13)),
                  const SizedBox(height: 8),
                  TextField(controller: endCtrl, decoration: const InputDecoration(labelText: '结束时间 (ISO)', border: OutlineInputBorder()), style: const TextStyle(fontSize: 13)),
                ] else ...[
                  TextField(controller: deadlineCtrl, decoration: const InputDecoration(labelText: '截止时间 (ISO)', border: OutlineInputBorder()), style: const TextStyle(fontSize: 13)),
                ],
              ],
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('取消')),
            FilledButton(
              onPressed: () => Navigator.pop(ctx, {
                'title': titleCtrl.text,
                'description': descCtrl.text,
                if (isEvent) 'start_time': startCtrl.text,
                if (isEvent) 'end_time': endCtrl.text,
                if (!isEvent) 'deadline': deadlineCtrl.text,
                if (!isEvent) 'priority': priority,
                'type': item['type'],
              }),
              child: const Text('保存'),
            ),
          ],
        ),
      ),
    );

    if (result != null) {
      setState(() => _results[index] = result);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: const Text('AI 助手')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            TextField(
              controller: _textController,
              maxLines: 3,
              decoration: const InputDecoration(
                labelText: '输入自然语言描述',
                hintText: '例如：明天下午3点到4点开会\n这周五前完成报告',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 8),
            SizedBox(
              width: double.infinity,
              height: 48,
              child: FilledButton.icon(
                onPressed: _loading ? null : _extract,
                icon: _loading
                    ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
                    : const Icon(Icons.auto_awesome),
                label: Text(_loading ? '分析中...' : 'AI 提取'),
              ),
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Text('提取结果 (${_results.length})', style: theme.textTheme.titleMedium),
                const Spacer(),
                if (_results.isNotEmpty)
                  TextButton(
                    onPressed: () async {
                      for (final item in List<Map<String, dynamic>>.from(_results)) {
                        await _addItem(item);
                      }
                    },
                    child: const Text('一键全部添加'),
                  ),
              ],
            ),
            const Divider(),
            Expanded(
              child: _results.isEmpty
                  ? Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.auto_awesome, size: 64, color: theme.colorScheme.primary.withValues(alpha: 0.4)),
                          const SizedBox(height: 16),
                          Text('输入文本后点击 AI 提取', style: theme.textTheme.bodyMedium?.copyWith(color: theme.colorScheme.onSurfaceVariant)),
                        ],
                      ),
                    )
                  : ListView.builder(
                      itemCount: _results.length,
                      itemBuilder: (context, index) {
                        final item = _results[index];
                        final isEvent = item['type'] == 'event';
                        return Card(
                          margin: const EdgeInsets.only(bottom: 8),
                          child: ListTile(
                            leading: CircleAvatar(
                              backgroundColor: isEvent ? Colors.blue : Colors.orange,
                              child: Icon(isEvent ? Icons.event : Icons.task, color: Colors.white),
                            ),
                            title: Text(item['title'] ?? ''),
                            subtitle: Text(isEvent
                                ? '日程: ${item['start_time'] ?? ''}'
                                : '待办: ${item['deadline'] ?? ''}'),
                            trailing: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                IconButton(
                                  icon: const Icon(Icons.edit, size: 18),
                                  onPressed: () => _editItem(index),
                                ),
                                FilledButton.tonalIcon(
                                  icon: const Icon(Icons.add, size: 16),
                                  label: const Text('添加'),
                                  onPressed: () => _addItem(item),
                                ),
                              ],
                            ),
                          ),
                        );
                      },
                    ),
            ),
          ],
        ),
      ),
    );
  }
}