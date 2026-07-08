import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:frontend/app.dart';

void main() {
  testWidgets('App should display Time Manager title', (WidgetTester tester) async {
    await tester.pumpWidget(const ProviderScope(child: TimeManagerApp()));
    expect(find.text('Time Manager'), findsOneWidget);
  });
}