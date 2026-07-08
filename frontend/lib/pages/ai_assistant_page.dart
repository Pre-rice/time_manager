import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/api_service.dart';
import '../providers/auth_provider.dart';

final _extractProvider = FutureProvider.autoDispose.family<List<dynamic>, String>((ref, text) async {
  if (text.isEmpty) return [];
  final api = ref.read(apiServiceProvider);
  if (!api.hasToken) return [];
  return api.extractFromText(text);
});

class AiAssistantPage extends ConsumerStatefulWidget {
  const AiAssistantPage({super.key});

  @override
  ConsumerState<AiAssistantPage> createState() => _AiAssistantPageState();
}

class _AiAssistantPageState extends ConsumerState<AiAssistantPage> {
  final _textController = TextEditingController();
  List<dynamic> _results = [];
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
      _results = await api.extractFromText(_textController.text.trim());
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('AI 提取失败，请检查 AI 配置')),
        );
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _addItem(Map<String, dynamic> item) async {
    try {
      final api = ref.read(apiServiceProvider);
      if (item['type'] == 'event') {
        await api.createEvent(item);
      } else {
        await api.createTask(item);
      }
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('已添加: ${item['title']}')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('添加失败')),
        );
      }
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
              maxLines: 4,
              decoration: const InputDecoration(
                labelText: '输入自然语言描述',
                hintText: '例如：明天下午3点到4点开会\n后天中午12点吃饭需要1小时\n这周五前完成报告',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
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
            const SizedBox(height: 12),
            Row(
              children: [
                Text('提取结果', style: theme.textTheme.titleMedium),
                const Spacer(),
                if (_results.isNotEmpty)
                  TextButton(
                    onPressed: () async {
                      for (final item in _results) {
                        await _addItem(item as Map<String, dynamic>);
                      }
                      if (mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(content: Text('已批量添加 ${_results.length} 项')),
                        );
                        setState(() => _results = []);
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
                        final item = _results[index] as Map<String, dynamic>;
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
                                ? '日程: ${item['start_time'] ?? '无时间'}'
                                : '待办: ${item['deadline'] ?? '无截止时间'}'),
                            trailing: FilledButton.tonalIcon(
                              icon: const Icon(Icons.add, size: 16),
                              label: const Text('添加'),
                              onPressed: () => _addItem(item),
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