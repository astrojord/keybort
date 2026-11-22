from .. import const
from ..helpers.stats import typing_sparkline
from ..models import TypingResult
from .base import UserScoped
from .inventory import KeyboardService


class TypingService(UserScoped):
    @staticmethod
    def board_names(owned):
        names = {}
        for inv in owned:
            names.setdefault(inv.keyboard_id, str(inv.obj))
        return names

    @staticmethod
    def summary(label, results):
        recent = results[-const.TYPING_RECENT_RACES :]
        recent_wpm = sum(result.wpm for result in recent) / len(recent)
        return {
            'label': label,
            'races': len(results),
            'best_wpm': max(result.wpm for result in results),
            'recent_wpm': recent_wpm,
            'recent_accuracy': sum(result.accuracy for result in recent) / len(recent),
            'sparkline': typing_sparkline(results[-const.TYPING_SPARKLINE_RACES :]),
        }

    def results(self):
        return list(
            TypingResult.objects.filter(user=self.user).order_by('created_at', 'pk')
        )

    def history(self, board_names, results):
        if not results:
            return []
        rows = [self.summary('All boards', results)]
        for keyboard_id, name in board_names.items():
            board_results = [r for r in results if r.keyboard_id == keyboard_id]
            if board_results:
                rows.append(self.summary(name, board_results))
        return rows

    def race_context(self, owned):
        names = self.board_names(owned)
        results = self.results()
        return {
            'race_boards': names,
            'race_selected_board': results[-1].keyboard_id if results else None,
            'race_history': self.history(names, results),
        }

    def record(self, *, keyboard_id, word_count, characters, mistakes, duration_ms):
        owned = KeyboardService(self.user).owned_keyboards()
        if keyboard_id and not owned.filter(keyboard_id=keyboard_id).exists():
            return False
        TypingResult.objects.create(
            user=self.user,
            keyboard_id=keyboard_id,
            word_count=word_count,
            characters=characters,
            mistakes=mistakes,
            duration_ms=duration_ms,
        )
        return True

    def history_context(self):
        owned = KeyboardService(self.user).owned_keyboards().order_by('-pk')
        return {'race_history': self.history(self.board_names(owned), self.results())}
