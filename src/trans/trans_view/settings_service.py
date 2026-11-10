from PySide6.QtWidgets import QMessageBox, QDialog
from src.ai import AiRoute, AiTarget
from src.system.load_save import load_data, save_data
import src.trans.preset as preset
import src.trans.trans_ai as trans_ai
from .model_utils import create_model_config, models_from_data
from .ui_factory import set_combo_value


def load_app_settings(settings_panel, model_panel, status_callback, log_callback):
    data = load_data()

    for target in AiRoute.TARGET_NAMES.keys():
        single_k, list_k, idx_k = AiRoute.get_storage_keys(target)
        api_val = str(data.get(single_k, '')).strip()
        keys_val = data.get(list_k, [])
        if not isinstance(keys_val, list):
            keys_val = [api_val] if api_val else []
        idx_val = data.get(idx_k, 0)

        if target == int(AiTarget.OLLAMA) and not api_val:
            api_val = str(data.get('ollama_url', 'http://localhost:11434')).strip()
            keys_val = [api_val]
            idx_val = 0

        if not api_val and keys_val:
            try:
                api_val = str(keys_val[idx_val]).strip()
            except (IndexError, TypeError):
                api_val = str(keys_val[0]).strip()

        if target == AiRoute.DEFAULT_TARGET:
            trans_ai.set_api_keys(keys_val, idx_val)
            api_val = api_val or trans_ai.API

        settings_panel.set_api_key(target, api_val)
        settings_panel.update_api_status_display(target, len(keys_val), idx_val)

    default_cfg = AiRoute.get_default_config(AiRoute.DEFAULT_TARGET)
    defaults = {
        'rpm': data.get('translate_rpm', default_cfg['rpm']),
        'temperature': data.get('translate_temperature', default_cfg['temperature']),
        'concurrency': data.get('translate_concurrency', default_cfg['concurrency']),
        'br_start': data.get('translate_br_start', default_cfg['br_start']),
        'isno_x': data.get('translate_isno_x', default_cfg['isno_x']),
        'thinking_budget': data.get('translate_thinking_budget', default_cfg['thinking_budget'])
    }

    model_panel.selected_models = models_from_data(data.get('translate_models'), defaults)
    if not model_panel.selected_models:
        default_model = data.get('translate_model') or AiRoute.DEFAULT_MODEL
        model_panel.selected_models = [create_model_config(default_model, defaults)]

    max_chars = str(data.get('translate_max_chars', 5000))
    set_combo_value(settings_panel.chars_combo, max_chars)

    settings_panel.glossary_enabled = bool(data.get('translate_glossary_enabled', True))
    settings_panel.update_glossary_button()

    if model_panel.selected_models:
        model_panel.active_model_index = -1
        model_panel.select_model(0, save_current=False)

    active_target = int(model_panel.selected_models[0].get('ai_target', AiRoute.DEFAULT_TARGET)) if model_panel.selected_models else AiRoute.DEFAULT_TARGET
    active_api = settings_panel.get_api_key(active_target)

    if active_target == int(AiTarget.OLLAMA):
        active_api = active_api or str(data.get('ollama_url', 'http://localhost:11434')).strip()
        settings_panel.set_api_key(active_target, active_api)
        model_panel.load_models(active_api, target_idx=active_target, manual=False)
        settings_panel.setCurrentIndex(0)
    elif active_api:
        model_panel.load_models(active_api, target_idx=active_target, manual=False)
        settings_panel.setCurrentIndex(0)
    else:
        settings_panel.setCurrentIndex(3)
        status_callback('API 키를 설정하세요.')

    log_callback('저장된 번역 설정을 불러왔습니다.')

def save_app_settings(settings_panel, model_panel, log_callback):
    try:
        data = load_data()

        for target, edit_widget in settings_panel.api_edits.items():
            single_k, list_k, idx_k = AiRoute.get_storage_keys(target)
            key_val = edit_widget.text().strip()

            if target == int(AiTarget.OLLAMA) and not key_val:
                key_val = str(data.get('ollama_url', 'http://localhost:11434')).strip()
                edit_widget.setText(key_val)

            keys_val = data.get(list_k, [])
            if not isinstance(keys_val, list):
                keys_val = []

            if key_val:
                if key_val not in keys_val:
                    keys_val.insert(0, key_val)
                    idx = 0
                else:
                    idx = keys_val.index(key_val)
            else:
                idx = 0

            data[single_k] = key_val
            data[list_k] = keys_val
            data[idx_k] = idx

            if target == int(AiTarget.OLLAMA):
                data['ollama_url'] = key_val

            if target == AiRoute.DEFAULT_TARGET and key_val:
                trans_ai.set_api_keys(keys_val, idx)

        save_data(data)

        configs = model_panel.get_model_configs()
        if not configs:
            return False

        first = configs[0]
        first_target = first.get('ai_target', AiRoute.DEFAULT_TARGET)

        data.update({
            'translate_ai_target': first_target,
            'translate_model': first['model'],
            'translate_models': configs,
            'translate_rpm': first['rpm'],
            'translate_temperature': first['temperature'],
            'translate_concurrency': first['concurrency'],
            'translate_br_start': first['br_start'],
            'translate_isno_x': first['isno_x'],
            'translate_thinking_budget': first['thinking_budget'],
            'translate_max_chars': int(settings_panel.chars_combo.currentText()),
            'translate_glossary_enabled': settings_panel.glossary_enabled
        })
        data['dictionary'] = data.get('dictionary') if isinstance(data.get('dictionary'), dict) else {}
        data['pre'] = data.get('pre') if isinstance(data.get('pre'), dict) else {}
        save_data(data)

        trans_ai.set_ai_target(first_target)
        log_callback('번역 기본 설정이 저장되었습니다.')
        return True
    except Exception as e:
        log_callback(f'설정 저장 중 오류: {e}')
        return False


def save_app_preset(settings_panel, model_panel, log_callback):
    name = settings_panel.preset_name_edit.text().strip()
    configs = model_panel.get_model_configs()

    if not name or not configs:
        return False

    try:
        data = load_data()
        data['pre'] = data.get('pre') if isinstance(data.get('pre'), dict) else {}
        data['pre'][name] = {
            'models': configs,
            'max_chars': int(settings_panel.chars_combo.currentText()),
            'glossary_enabled': settings_panel.glossary_enabled
        }
        save_data(data)
        settings_panel.preset_name_edit.setText(name)
        settings_panel.preset_status.setText(f'현재 프리셋: {name}')
        log_callback(f'프리셋 저장 완료: {name}')
        return True
    except Exception:
        return False


def load_app_preset(settings_panel, model_panel, parent_dialog, log_callback):
    data = load_data()
    presets = data.get('pre', {})
    if not isinstance(presets, dict) or not presets:
        QMessageBox.information(parent_dialog, '프리셋', '저장된 프리셋이 없습니다.')
        return False

    dialog = preset.PresetLoadDialog(presets, parent_dialog)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return False

    name = dialog.selected_name
    presetq = presets.get(name)
    if not isinstance(presetq, dict):
        return False

    models = models_from_data(presetq.get('models'), presetq)
    if not models:
        return False

    model_panel.selected_models = models
    set_combo_value(settings_panel.chars_combo, presetq.get('max_chars', 5000))
    settings_panel.glossary_enabled = bool(presetq.get('glossary_enabled', True))
    settings_panel.update_glossary_button()
    settings_panel.preset_name_edit.setText(name)
    settings_panel.preset_status.setText(f'현재 프리셋: {name}')
    model_panel.select_model(0, save_current=False)
    log_callback(f'프리셋 불러오기 완료: {name}')
    return True