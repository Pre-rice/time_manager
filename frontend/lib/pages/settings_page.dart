import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';
import '../services/api_service.dart';
import '../providers/auth_provider.dart';
import '../providers/week_start_provider.dart';

class SettingsPage extends ConsumerStatefulWidget {
  const SettingsPage({super.key});

  @override
  ConsumerState<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends ConsumerState<SettingsPage> {
  final _apiKeyController = TextEditingController();
  final _endpointController = TextEditingController();
  final _modelController = TextEditingController(text: 'gpt-4o-mini');
  bool _loading = false;
  bool _showKey = false;
  bool _hasConfig = false;

  // 复旦配置
  final _studentIdController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _fudanLoading = false;
  bool _fudanConnected = false;
  String? _fudanStudentId;
  String? _fudanLastSync;
  bool _showPassword = false;

  @override
  void initState() {
    super.initState();
    _loadConfig();
    _loadFudanStatus();
  }

  @override
  void dispose() {
    _apiKeyController.dispose();
    _endpointController.dispose();
    _modelController.dispose();
    _studentIdController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _loadFudanStatus() async {
    final api = ref.read(apiServiceProvider);
    if (!api.hasToken) return;
    final status = await api.getFudanStatus();
    if (mounted) {
      setState(() {
        _fudanConnected = status['connected'] == true;
        _fudanStudentId = status['student_id'] as String?;
        _fudanLastSync = status['last_sync_at'] as String?;
        if (_fudanConnected && _fudanStudentId != null) {
          _studentIdController.text = _fudanStudentId!;
        }
      });
    }
  }

  Future<void> _connectFudan() async {
    if (_studentIdController.text.isEmpty || _passwordController.text.isEmpty) return;
    setState(() => _fudanLoading = true);
    try {
      final api = ref.read(apiServiceProvider);
      final result = await api.connectFudan(
        _studentIdController.text,
        _passwordController.text,
      );
      if (mounted) {
        if (result['success'] == true) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('复旦教务系统连接成功')),
          );
          _passwordController.clear();
          await _loadFudanStatus();
        } else {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(result['message'] ?? '连接失败')),
          );
        }
      }
    } catch (e) {
      if (mounted) {
        String errorMsg = '连接失败';
        if (e is DioException) {
          try {
            final data = e.response?.data;
            if (data is Map && data['detail'] != null) {
              final detail = data['detail'];
              if (detail is List && detail.isNotEmpty) {
                errorMsg = detail[0]['msg'] ?? '连接失败';
              } else if (detail is String) {
                errorMsg = detail;
              }
            }
            if (data is Map && data['message'] != null) {
              errorMsg = data['message'];
            }
          } catch (_) {}
        } else {
          errorMsg = e.toString();
        }
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(errorMsg)),
        );
      }
    } finally {
      if (mounted) setState(() => _fudanLoading = false);
    }
  }

  Future<void> _disconnectFudan() async {
    setState(() => _fudanLoading = true);
    try {
      final api = ref.read(apiServiceProvider);
      await api.disconnectFudan();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('已断开复旦连接')),
        );
        setState(() {
          _fudanConnected = false;
          _fudanStudentId = null;
          _fudanLastSync = null;
        });
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('断开连接失败')),
        );
      }
    } finally {
      if (mounted) setState(() => _fudanLoading = false);
    }
  }

  Future<void> _loadConfig() async {
    final api = ref.read(apiServiceProvider);
    if (!api.hasToken) return;
    final config = await api.getAIConfig();
    if (config != null && mounted) {
      setState(() {
        _hasConfig = true;
        _endpointController.text = config['api_endpoint'] ?? '';
        _modelController.text = config['model_name'] ?? 'gpt-4o-mini';
      });
    }
  }

  Future<void> _save() async {
    if (_apiKeyController.text.isEmpty) return;
    setState(() => _loading = true);
    try {
      final api = ref.read(apiServiceProvider);
      await api.saveAIConfig({
        'api_key': _apiKeyController.text,
        'model_name': _modelController.text,
        if (_endpointController.text.isNotEmpty) 'api_endpoint': _endpointController.text,
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('AI 配置已保存')),
        );
        setState(() => _hasConfig = true);
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('保存失败')),
        );
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _delete() async {
    setState(() => _loading = true);
    try {
      final api = ref.read(apiServiceProvider);
      await api.deleteAIConfig();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('AI 配置已删除')),
        );
        setState(() {
          _hasConfig = false;
          _apiKeyController.clear();
          _endpointController.clear();
          _modelController.text = 'gpt-4o-mini';
        });
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('删除失败')),
        );
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final weekStart = ref.watch(weekStartProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('设置')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(Icons.calendar_view_week, color: theme.colorScheme.primary),
                      const SizedBox(width: 8),
                      Text('每周起始日', style: theme.textTheme.titleMedium),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Text('周日', style: theme.textTheme.bodyMedium),
                      Switch(
                        value: weekStart.isMonday,
                        onChanged: (_) => weekStart.toggle(),
                      ),
                      Text('周一', style: theme.textTheme.bodyMedium),
                    ],
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(Icons.auto_awesome, color: theme.colorScheme.primary),
                      const SizedBox(width: 8),
                      Text('AI 配置', style: theme.textTheme.titleMedium),
                      const Spacer(),
                      if (_hasConfig)
                        TextButton.icon(
                          icon: const Icon(Icons.delete_outline),
                          label: const Text('删除'),
                          onPressed: _delete,
                        ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  TextFormField(
                    controller: _apiKeyController,
                    obscureText: !_showKey,
                    decoration: InputDecoration(
                      labelText: 'API Key',
                      border: const OutlineInputBorder(),
                      suffixIcon: IconButton(
                        icon: Icon(_showKey ? Icons.visibility_off : Icons.visibility),
                        onPressed: () => setState(() => _showKey = !_showKey),
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _endpointController,
                    decoration: const InputDecoration(
                      labelText: 'API 地址（可选）',
                      hintText: 'https://api.openai.com/v1',
                      border: OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _modelController,
                    decoration: const InputDecoration(
                      labelText: '模型名称',
                      hintText: 'gpt-4o-mini',
                      border: OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: 16),
                  SizedBox(
                    width: double.infinity,
                    height: 48,
                    child: FilledButton(
                      onPressed: _loading ? null : _save,
                      child: _loading
                          ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
                          : const Text('保存配置'),
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(Icons.school, color: theme.colorScheme.primary),
                      const SizedBox(width: 8),
                      Text('复旦教务连接', style: theme.textTheme.titleMedium),
                      const Spacer(),
                      if (_fudanConnected)
                        Chip(
                          avatar: const Icon(Icons.check_circle, size: 16, color: Colors.green),
                          label: const Text('已连接'),
                          visualDensity: VisualDensity.compact,
                        )
                      else
                        Chip(
                          avatar: const Icon(Icons.link_off, size: 16),
                          label: const Text('未连接'),
                          visualDensity: VisualDensity.compact,
                        ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  if (_fudanConnected) ...[
                    if (_fudanStudentId != null)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: Text('学号：$_fudanStudentId', style: theme.textTheme.bodyMedium),
                      ),
                    if (_fudanLastSync != null)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 16),
                        child: Text('上次同步：${_fudanLastSync!.substring(0, 16).replaceAll('T', ' ')}',
                            style: theme.textTheme.bodySmall?.copyWith(color: theme.colorScheme.onSurfaceVariant)),
                      ),
                    SizedBox(
                      width: double.infinity,
                      height: 48,
                      child: OutlinedButton.icon(
                        icon: _fudanLoading
                            ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                            : const Icon(Icons.link_off),
                        label: const Text('断开连接'),
                        onPressed: _fudanLoading ? null : _disconnectFudan,
                      ),
                    ),
                  ] else ...[
                    TextFormField(
                      controller: _studentIdController,
                      decoration: const InputDecoration(
                        labelText: '学号',
                        hintText: '请输入复旦学号',
                        border: OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: _passwordController,
                      obscureText: !_showPassword,
                      decoration: InputDecoration(
                        labelText: 'UIS 密码',
                        border: const OutlineInputBorder(),
                        suffixIcon: IconButton(
                          icon: Icon(_showPassword ? Icons.visibility_off : Icons.visibility),
                          onPressed: () => setState(() => _showPassword = !_showPassword),
                        ),
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text('密码将被加密存储，仅用于自动同步课表/考试/作业',
                        style: theme.textTheme.bodySmall?.copyWith(color: theme.colorScheme.onSurfaceVariant)),
                    const SizedBox(height: 16),
                    SizedBox(
                      width: double.infinity,
                      height: 48,
                      child: FilledButton.icon(
                        icon: _fudanLoading
                            ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                            : const Icon(Icons.link),
                        label: const Text('连接复旦教务'),
                        onPressed: _fudanLoading ? null : _connectFudan,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(Icons.info_outline, color: theme.colorScheme.primary),
                      const SizedBox(width: 8),
                      Text('使用说明', style: theme.textTheme.titleMedium),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text('• 支持任何 OpenAI 兼容的 API', style: theme.textTheme.bodySmall),
                  Text('• 如需使用 Azure OpenAI，填写对应的 API 地址', style: theme.textTheme.bodySmall),
                  Text('• API Key 将被加密存储，不会明文暴露', style: theme.textTheme.bodySmall),
                  Text('• 推荐使用 gpt-4o-mini，速度快且成本低', style: theme.textTheme.bodySmall),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}