import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:table_calendar/table_calendar.dart';

final weekStartProvider = ChangeNotifierProvider<WeekStartNotifier>((ref) {
  return WeekStartNotifier();
});

class WeekStartNotifier extends ChangeNotifier {
  StartingDayOfWeek _startingDayOfWeek = StartingDayOfWeek.monday;
  bool _isLoaded = false;

  StartingDayOfWeek get startingDayOfWeek => _startingDayOfWeek;
  bool get isMonday => _startingDayOfWeek == StartingDayOfWeek.monday;
  bool get isLoaded => _isLoaded;

  WeekStartNotifier() {
    _load();
  }

  Future<void> _load() async {
    final prefs = await SharedPreferences.getInstance();
    final stored = prefs.getString('week_start_day');
    _startingDayOfWeek = stored == 'sunday' ? StartingDayOfWeek.sunday : StartingDayOfWeek.monday;
    _isLoaded = true;
    notifyListeners();
  }

  Future<void> setStartingDayOfWeek(StartingDayOfWeek day) async {
    _startingDayOfWeek = day;
    notifyListeners();
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('week_start_day', day == StartingDayOfWeek.sunday ? 'sunday' : 'monday');
  }

  Future<void> toggle() async {
    if (_startingDayOfWeek == StartingDayOfWeek.monday) {
      await setStartingDayOfWeek(StartingDayOfWeek.sunday);
    } else {
      await setStartingDayOfWeek(StartingDayOfWeek.monday);
    }
  }
}