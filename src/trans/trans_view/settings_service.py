from PySide6.QtWidgets import QMessageBox, QDialog
from src.system.load_save import load_data, save_data
import src.trans.preset as preset
import src.trans.trans_ai as trans_ai
from .model_utils import create_model_config, models_from_data
from .ui_factory import set_combo_value


def load_app_settings(settings_panel, model_panel, status_callback, log_callback):
    data = load_data()
    api = str(data.get('api', '')).strip()
    api_keys = data.get('api_keys', [])
    if not isinstance(api_keys, list):
        api_keys = [api] if api else []
    api_index = data.get('api_index', 0)

    trans_ai.set_api_keys(api_keys, api_index)

    current_api = trans_ai.API or api
    settings_panel.api_edit.setText(current_api)
    settings_panel.update_api_status_display(len(trans_ai.API_KEYS), trans_ai.API_INDEX)

    defaults = {
        'rpm': data.get('translate_rpm', 15),
        'temperature': data.get('translate_temperature', 0.1),
        'concurrency': data.get('translate_concurrency', 4),
        'br_start': data.get('translate_br_start', 0),
        'isno_x': data.get('translate_isno_x', False),
        'thinking_budget': data.get('translate_thinking_budget', '기본값')
    }

    model_panel.selected_models = models_from_data(data.get('translate_models'), defaults)
    if not model_panel.selected_models and data.get('translate_model'):
        model_panel.selected_models = [create_model_config(data['translate_model'], defaults)]

    max_chars = str(data.get('translate_max_chars', 5000))
    set_combo_value(settings_panel.chars_combo, max_chars)

    settings_panel.glossary_enabled = bool(data.get('translate_glossary_enabled', True))
    settings_panel.update_glossary_button()

    if model_panel.selected_models:
        model_panel.active_model_index = -1
        model_panel.select_model(0, save_current=False)

    if not current_api:
        settings_panel.setCurrentIndex(3)
        status_callback('Gemini API 키를 설정하세요.')
    else:
        settings_panel.setCurrentIndex(0)
        try:
            model_panel.load_gemini_models(current_api)
        except Exception as e:
            log_callback(f'자동 모델 조회 실패: {e}')

    log_callback('저장된 번역 설정을 불러왔습니다.')


def save_app_settings(settings_panel, model_panel, log_callback):
    api = settings_panel.api_edit.text().strip()
    configs = model_panel.get_model_configs()

    if not api or not configs:
        return False

    try:
        data = load_data()
        first = configs[0]
        
        api_keys = data.get('api_keys', [])
        if not isinstance(api_keys, list) or not api_keys:
            api_keys = [api]
        api_index = data.get('api_index', 0)

        data.update({
            'api': api,
            'api_keys': api_keys,
            'api_index': api_index,
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
        log_callback('번역 기본 설정이 저장되었습니다.')
        return True
    except Exception:
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