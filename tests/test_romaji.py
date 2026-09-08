from lib.romaji import (
    is_kana_only_surface,
    hiraganize_kana_surface,
    katakana_to_hiragana,
    romaji_to_hiragana,
)


def test_usada_pekora():
    assert romaji_to_hiragana("Usada Pekora") == "うさだぺこら"


def test_kenmochi_toya():
    # 出典に無い長音の知識（「とうや」）は機械化しない。素直な音読みの「とや」でよい。
    assert romaji_to_hiragana("Kenmochi Toya") == "けんもちとや"


def test_hikasa_tomoshika():
    assert romaji_to_hiragana("Hikasa Tomoshika") == "ひかさともしか"


def test_word_order_follows_surface_not_input_order():
    # 出典の日本語表記が「緋笠トモシカ」（姓+片仮名の名）なら、
    # ローマ字が逆順で渡されても表記の語順に揃える。
    assert romaji_to_hiragana("Tomoshika Hikasa", surface="緋笠トモシカ") == "ひかさともしか"


def test_kuzuha_single_word():
    assert romaji_to_hiragana("Kuzuha") == "くずは"


def test_higuchi_kaede():
    assert romaji_to_hiragana("Higuchi Kaede") == "ひぐちかえで"


def test_shirakami_fubuki():
    assert romaji_to_hiragana("Shirakami Fubuki") == "しらかみふぶき"


def test_houshou_long_vowel_ou():
    # 「Marine」は本来 マリン（3モーラ）だが、英単語の綴りをそのまま活動名にした
    # ケースは語尾の黙字 e を素直な逐語ヘボン変換では判別できない（machine 化の限界。
    # needs_review=yes 前提なので、ここでは「ou」の連続長音が崩れないことだけ確認する）。
    assert romaji_to_hiragana("Houshou") == "ほうしょう"


def test_hoshimachi_suisei():
    assert romaji_to_hiragana("Hoshimachi Suisei") == "ほしまちすいせい"


def test_geminate_consonant():
    # 撥音でなく促音（同一子音の連続）の確認用サンプル。
    assert romaji_to_hiragana("Kassai") == "かっさい"


def test_standalone_c_as_k():
    # 英語風の綴りで c が単独で /k/ を表すケース（実在の hololive 表記）。
    assert romaji_to_hiragana("Robocosan") == "ろぼこさん"
    assert romaji_to_hiragana("Choco") == "ちょこ"


def test_namba_style_m_before_b():
    assert romaji_to_hiragana("Namba") == "なんば"


def test_n_before_consonant_is_n_mora():
    assert romaji_to_hiragana("Kenta") == "けんた"


def test_n_before_vowel_is_na_row():
    assert romaji_to_hiragana("Kana") == "かな"


def test_apostrophe_n_before_vowel_is_explicit_n_mora():
    assert romaji_to_hiragana("Jun'ichi") == "じゅんいち"


def test_yoon():
    assert romaji_to_hiragana("Kyoko") == "きょこ"


def test_v_row():
    assert romaji_to_hiragana("Ai Va") == "あいゔぁ"


def test_unmappable_letter_returns_none():
    # x/q は本モジュールのモーラ表に無い（ピンイン系ローマ字・英語圏名などを想定した失敗ケース）。
    assert romaji_to_hiragana("Xingxi") is None
    # 実在の enName（NIJISANJI EN "Vox Akuma"）も x を含み、この規則により変換不能になる。
    # これは正しい失敗（needs_review=yes・reading 空で扱う）。
    assert romaji_to_hiragana("Vox Akuma") is None


def test_empty_input_returns_none():
    assert romaji_to_hiragana("") is None
    assert romaji_to_hiragana("   ") is None


def test_is_kana_only_surface():
    assert is_kana_only_surface("ときのそら") is True
    assert is_kana_only_surface("アキ・ローゼンタール") is True
    assert is_kana_only_surface("白上フブキ") is False
    assert is_kana_only_surface("葛葉") is False


def test_hiraganize_kana_surface_drops_separator():
    assert hiraganize_kana_surface("アキ・ローゼンタール") == "あきろーぜんたーる"


def test_katakana_to_hiragana_keeps_choonpu():
    assert katakana_to_hiragana("ラーメン") == "らーめん"


def test_katakana_to_hiragana_vu():
    assert katakana_to_hiragana("ヴォックス") == "ゔぉっくす"
