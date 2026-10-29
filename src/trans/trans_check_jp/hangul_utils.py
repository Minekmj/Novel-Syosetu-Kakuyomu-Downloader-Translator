CHOSUNG = ['ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']
JUNGSUNG = ['ㅏ', 'ㅐ', 'ㅑ', 'ㅒ', 'ㅓ', 'ㅔ', 'ㅕ', 'ㅖ', 'ㅗ', 'ㅘ', 'ㅙ', 'ㅚ', 'ㅛ', 'ㅜ', 'ㅝ', 'ㅞ', 'ㅟ', 'ㅠ', 'ㅡ', 'ㅢ', 'ㅣ']
JONGSUNG = ['', 'ㄱ', 'ㄲ', 'ㄳ', 'ㄴ', 'ㄵ', 'ㄶ', 'ㄷ', 'ㄹ', 'ㄺ', 'ㄻ', 'ㄼ', 'ㄽ', 'ㄾ', 'ㄿ', 'ㅀ', 'ㅁ', 'ㅂ', 'ㅄ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']


def decompose_hangul(char):
    if not ('가' <= char <= '힣'):
        return None
    code = ord(char) - ord('가')
    return (CHOSUNG[code // (21 * 28)], JUNGSUNG[(code % (21 * 28)) // 28], JONGSUNG[code % 28])


def compose_hangul(cho, jung, jong=''):
    try:
        return chr(0xAC00 + (CHOSUNG.index(cho) * 21 * 28) + (JUNGSUNG.index(jung) * 28) + JONGSUNG.index(jong))
    except ValueError:
        return cho + jung + jong


def attach_jongsung(hangul_char: str, target_jong: str) -> str:
    decomp = decompose_hangul(hangul_char)
    if not decomp:
        return hangul_char + target_jong
    cho, jung, jong = decomp
    if jong == '':
        return compose_hangul(cho, jung, target_jong)
    return hangul_char + target_jong