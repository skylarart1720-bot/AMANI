"""Seed offline navigation and referral replies; never overwrites edited translations."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "apps/orchestrator/src/locales"
# ISO/BCP-47 identifiers. Names are intentionally kept in their own scripts.
ROWS = [
 ("en","English","English"), ("fr","Français","French"),
 ("ak","Twi / Akan","Akan (Twi)"), ("ee","Eʋegbe","Ewe"), ("gaa","Gã","Ga"),
 ("ha","Hausa","Hausa"), ("yo","Yorùbá","Yoruba"), ("ig","Igbo","Igbo"),
 ("sw","Kiswahili","Swahili"), ("zu","isiZulu","Zulu"), ("am","አማርኛ","Amharic"),
 ("so","Soomaali","Somali"), ("ar","العربية","Arabic"), ("es","Español","Spanish"),
 ("pt","Português","Portuguese"), ("de","Deutsch","German"), ("it","Italiano","Italian"),
 ("hi","हिन्दी","Hindi"), ("zh-CN","简体中文","Simplified Chinese"), ("ru","Русский","Russian"),
 ("uk","Українська","Ukrainian"), ("bn","বাংলা","Bengali"), ("tr","Türkçe","Turkish"), ("ur","اردو","Urdu")
]
KEYS = "Get support|Support topics|Find help|Check a link|Language|Online|Offline|Staff|Super Admin|Sign in|Password|Send|Privacy and safeguarding|Delete conversation|Continue with web support|Official website".split("|")
CORE = {
"ak":"Nya mmoa|Mmoa nsɛm|Hwehwɛ mmoa|Hwɛ link bi|Kasa|Wɔ intanɛt so|Nni intanɛt so|Adwumayɛfo|Panyin hwɛfo|Kɔ mu|Ahintasɛmfua|Fa kɔ|Ahintasɛm ne ahobammɔ|Pepa nkɔmmɔ no|Toa so wɔ wɛb so|Ahyehyɛde no wɛbsaet",
"ee":"Xɔ kpeɖeŋu|Kpeɖeŋu ƒe nyawo|Di kpeɖeŋu|Kpɔ kadodo aɖe dzi|Gbe|Le intanɛt dzi|Mele intanɛt dzi o|Dɔwɔlawo|Dzitsila gã|Ge ɖe eme|Nyagbe ɣaɣla|Dɔe|Nyawo ƒe ɣaɣla kple dedienɔnɔ|Tutɔ dzeɖoɖo la|Yi edzi le wɛb dzi|Dɔwɔƒe la ƒe wɛbsaet",
"ha":"Samu tallafi|Batutuwan tallafi|Nemi taimako|Duba hanyar haɗi|Harshe|Yana kan layi|Ba ya kan layi|Ma'aikata|Babban mai gudanarwa|Shiga|Kalmar sirri|Aika|Sirri da kariya|Goge tattaunawa|Ci gaba da tallafin yanar gizo|Shafin hukuma",
"yo":"Gba ìrànlọ́wọ́|Àwọn kókó ìrànlọ́wọ́|Wá ìrànlọ́wọ́|Ṣàyẹ̀wò ìjápọ̀|Èdè|Wà lórí ayélujára|Kò sí lórí ayélujára|Òṣìṣẹ́|Alábòójútó àgbà|Wọlé|Ọ̀rọ̀ aṣínà|Firanṣẹ́|Àṣírí àti ààbò|Pa ìjíròrò rẹ́|Tẹ̀síwájú pẹ̀lú ìrànlọ́wọ́ wẹ́ẹ̀bù|Ojúlé ìjọba",
"ig":"Nweta nkwado|Isiokwu nkwado|Chọọ enyemaka|Lelee njikọ|Asụsụ|Nọ n'ịntanetị|Anọghị n'ịntanetị|Ndị ọrụ|Onye nchịkwa isi|Banye|Okwuntughe|Zipu|Nzuzo na nchekwa|Hichapụ mkparịta ụka|Gaa n'ihu na nkwado weebụ|Weebụsaịtị gọọmentị",
"sw":"Pata msaada|Mada za msaada|Tafuta msaada|Kagua kiungo|Lugha|Mtandaoni|Hayupo mtandaoni|Wafanyakazi|Msimamizi mkuu|Ingia|Nenosiri|Tuma|Faragha na ulinzi|Futa mazungumzo|Endelea na msaada wa wavuti|Tovuti rasmi",
"zu":"Thola usizo|Izihloko zosizo|Funa usizo|Hlola isixhumanisi|Ulimi|Ku-inthanethi|Akukho ku-inthanethi|Abasebenzi|Umphathi omkhulu|Ngena|Iphasiwedi|Thumela|Ubumfihlo nokuvikelwa|Susa ingxoxo|Qhubeka nosizo lwewebhu|Iwebhusayithi esemthethweni",
"am":"ድጋፍ ያግኙ|የድጋፍ ርዕሶች|እርዳታ ይፈልጉ|አገናኝ ያረጋግጡ|ቋንቋ|በመስመር ላይ|ከመስመር ውጭ|ሠራተኞች|ዋና አስተዳዳሪ|ይግቡ|የይለፍ ቃል|ላክ|ግላዊነትና ጥበቃ|ውይይት ሰርዝ|በድር ድጋፍ ይቀጥሉ|ኦፊሴላዊ ድረ ገጽ",
"so":"Hel taageero|Mawduucyada taageerada|Raadi caawimo|Hubi xiriir|Luqad|Khadka ayuu ku jiraa|Khadka kama jiro|Shaqaalaha|Maamulaha guud|Soo gal|Furaha sirta|Dir|Asturnaanta iyo ilaalinta|Tirtir wada hadalka|Sii wad taageerada webka|Bogga rasmiga ah",
"ar":"احصل على الدعم|مواضيع الدعم|ابحث عن مساعدة|تحقق من رابط|اللغة|متصل|غير متصل|الموظفون|المسؤول الرئيسي|تسجيل الدخول|كلمة المرور|إرسال|الخصوصية والحماية|حذف المحادثة|متابعة الدعم عبر الويب|الموقع الرسمي",
"es":"Obtener apoyo|Temas de apoyo|Buscar ayuda|Comprobar un enlace|Idioma|En línea|Desconectado|Personal|Administrador principal|Iniciar sesión|Contraseña|Enviar|Privacidad y protección|Eliminar conversación|Continuar con el apoyo web|Sitio oficial",
"pt":"Obter apoio|Temas de apoio|Encontrar ajuda|Verificar um link|Idioma|Online|Offline|Equipa|Administrador principal|Iniciar sessão|Palavra-passe|Enviar|Privacidade e proteção|Eliminar conversa|Continuar com o apoio web|Site oficial",
"de":"Unterstützung erhalten|Hilfethemen|Hilfe finden|Link prüfen|Sprache|Online|Offline|Mitarbeitende|Hauptadministrator|Anmelden|Passwort|Senden|Datenschutz und Schutzmaßnahmen|Gespräch löschen|Mit Web-Unterstützung fortfahren|Offizielle Website",
"it":"Ricevi supporto|Argomenti di supporto|Trova aiuto|Controlla un link|Lingua|Online|Offline|Personale|Amministratore principale|Accedi|Password|Invia|Privacy e protezione|Elimina conversazione|Continua con il supporto web|Sito ufficiale",
"hi":"सहायता प्राप्त करें|सहायता के विषय|मदद खोजें|लिंक जाँचें|भाषा|ऑनलाइन|ऑफ़लाइन|कर्मचारी|मुख्य प्रशासक|लॉग इन करें|पासवर्ड|भेजें|गोपनीयता और सुरक्षा|बातचीत मिटाएँ|वेब सहायता जारी रखें|आधिकारिक वेबसाइट",
"zh-CN":"获取支持|支持主题|寻找帮助|检查链接|语言|在线|离线|工作人员|超级管理员|登录|密码|发送|隐私与保护|删除对话|继续使用网页支持|官方网站",
"ru":"Получить поддержку|Темы поддержки|Найти помощь|Проверить ссылку|Язык|В сети|Не в сети|Сотрудники|Главный администратор|Войти|Пароль|Отправить|Конфиденциальность и защита|Удалить разговор|Продолжить поддержку на сайте|Официальный сайт",
"uk":"Отримати підтримку|Теми підтримки|Знайти допомогу|Перевірити посилання|Мова|Онлайн|Офлайн|Працівники|Головний адміністратор|Увійти|Пароль|Надіслати|Конфіденційність і захист|Видалити розмову|Продовжити підтримку на сайті|Офіційний сайт",
"bn":"সহায়তা পান|সহায়তার বিষয়|সাহায্য খুঁজুন|লিংক যাচাই করুন|ভাষা|অনলাইন|অফলাইন|কর্মীরা|প্রধান প্রশাসক|প্রবেশ করুন|পাসওয়ার্ড|পাঠান|গোপনীয়তা ও সুরক্ষা|কথোপকথন মুছুন|ওয়েব সহায়তা চালিয়ে যান|সরকারি ওয়েবসাইট",
"tr":"Destek alın|Destek konuları|Yardım bulun|Bağlantıyı kontrol edin|Dil|Çevrimiçi|Çevrimdışı|Personel|Baş yönetici|Giriş yapın|Şifre|Gönder|Gizlilik ve koruma|Konuşmayı sil|Web desteğine devam et|Resmî web sitesi",
"ur":"مدد حاصل کریں|معاونت کے موضوعات|مدد تلاش کریں|لنک چیک کریں|زبان|آن لائن|آف لائن|عملہ|مرکزی منتظم|لاگ ان کریں|پاس ورڈ|بھیجیں|رازداری اور تحفظ|گفتگو حذف کریں|ویب معاونت جاری رکھیں|سرکاری ویب سائٹ"
}
FALLBACK = {
"fr":"Consultez les liens officiels ci-dessous pour vérifier les services et leur disponibilité. Je ne peux pas fournir de conseil juridique ou médical personnalisé.",
"ak":"Hwɛ mmoa ho link ahorow a ɛwɔ ase no na bisa wɔn nnwuma ne wɔn bere. Mintumi mma wo ankasa mmara anaa aduruyɛ afotu.",
"ee":"Kpɔ kpeɖeŋu ƒe kadodowo le afi sia te eye nàbia dɔwɔƒewo ŋu. Nyemate ŋu ana se alo atike ŋuti aɖaŋu tɔxɛ wò o.",
"ha":"Yi amfani da hanyoyin hukuma da ke ƙasa don tabbatar da ayyuka da samuwarsu. Ba zan iya ba da shawarar shari'a ko likita ta mutum ba.",
"yo":"Lo àwọn ìjápọ̀ ojúlówó ní ìsàlẹ̀ láti ṣàyẹ̀wò iṣẹ́ àti ìgbà tí wọ́n wà. Mi ò lè fún ọ ní ìmọ̀ràn òfin tàbí ìṣègùn ti ara ẹni.",
"ig":"Jiri njikọ ndị dị n'okpuru lelee ọrụ na oge ha dị. Enweghị m ike inye ndụmọdụ iwu ma ọ bụ ọgwụ maka gị onwe gị.",
"sw":"Tumia viungo rasmi hapa chini kuthibitisha huduma na upatikanaji. Siwezi kutoa ushauri binafsi wa kisheria au wa matibabu.",
"zu":"Sebenzisa izixhumanisi ezisemthethweni ezingezansi ukuqinisekisa izinsizakalo nokutholakala kwazo. Angikwazi ukunikeza iseluleko somthetho noma sezokwelapha somuntu ngamunye.",
"am":"አገልግሎቶችንና ተገኝነታቸውን ለማረጋገጥ ከታች ያሉትን ኦፊሴላዊ አገናኞች ይጠቀሙ። የግል የሕግ ወይም የሕክምና ምክር መስጠት አልችልም።",
"so":"Isticmaal xiriirrada rasmiga ah ee hoose si aad u hubiso adeegyada iyo helitaankooda. Ma bixin karo talo sharci ama caafimaad oo gaar kuu ah.",
"ar":"استخدم روابط الدعم الرسمية أدناه للتحقق من الخدمات وتوفرها. لا يمكنني تقديم مشورة قانونية أو طبية فردية.",
"es":"Utiliza los enlaces oficiales de abajo para comprobar los servicios y su disponibilidad. No puedo ofrecer asesoramiento jurídico o médico individual.",
"pt":"Use os links oficiais abaixo para confirmar os serviços e a disponibilidade. Não posso dar aconselhamento jurídico ou médico individual.",
"de":"Prüfen Sie die Leistungen und Verfügbarkeit über die offiziellen Links unten. Ich kann keine individuelle Rechtsberatung oder medizinische Beratung geben.",
"it":"Usa i link ufficiali qui sotto per verificare servizi e disponibilità. Non posso fornire consulenza legale o medica individuale.",
"hi":"सेवाओं और उपलब्धता की पुष्टि के लिए नीचे दिए आधिकारिक लिंक देखें। मैं व्यक्तिगत कानूनी या चिकित्सा सलाह नहीं दे सकता।",
"zh-CN":"请通过下方的官方支持链接确认服务及其可用性。我无法提供针对个人的法律或医疗建议。",
"ru":"Проверьте услуги и их доступность по официальным ссылкам ниже. Я не могу давать индивидуальные юридические или медицинские рекомендации.",
"uk":"Перевірте послуги та їхню доступність за офіційними посиланнями нижче. Я не можу надавати індивідуальні юридичні або медичні поради.",
"bn":"পরিষেবা ও প্রাপ্যতা যাচাই করতে নিচের সরকারি সহায়তা লিংকগুলি দেখুন। আমি ব্যক্তিগত আইনি বা চিকিৎসা পরামর্শ দিতে পারি না।",
"tr":"Hizmetleri ve uygunluğu doğrulamak için aşağıdaki resmî bağlantıları kullanın. Kişiye özel hukuki veya tıbbi tavsiye veremem.",
"ur":"خدمات اور دستیابی کی تصدیق کے لیے نیچے دیے گئے سرکاری روابط استعمال کریں۔ میں انفرادی قانونی یا طبی مشورہ نہیں دے سکتا۔"
}
URGENT = {
"ak":"Sɛ wowɔ asiane kɛse mu wɔ Ghana a, frɛ 112 seesei. Sɛ wowɔ Ghana akyi a, frɛ ɛhɔ ntɛmpɛ mmoa. Sɛ ɛbɛyɛ yiye a, hu obi a wugye no di. Yɛde wo adesrɛ no di kan, nanso yɛrentumi nhyɛ bɔ sɛ obi bɛbua wo.",
"ee":"Ne nèle afɔku me le Ghana la, yɔ 112 fifia. Le Ghana godo la, yɔ afima ƒe bubuɖoɖo ƒe kpeɖeŋu. Ne ate ŋu la, yɔ ame si nèka ɖe dzi. Wo adesrɛ la le ŋgɔ, gake amegbetɔ ƒe ŋuɖoɖo mele ŋugbe o.",
"ha":"Idan kana cikin haɗari na gaggawa a Ghana, kira 112 yanzu. A wajen Ghana, tuntubi ayyukan gaggawa na yankinka. Ka nemi wanda ka amince da shi idan zai yiwu. Buƙatarka tana da fifiko, amma ba a tabbatar da amsar mutum ba.",
"yo":"Tí o bá wà nínú ewu lẹ́sẹ̀kẹsẹ̀ ní Ghana, pe 112 báyìí. Ní òde Ghana, kan sí iṣẹ́ pajawiri agbègbè rẹ. Kan sí ẹni tí o gbẹ́kẹ̀ lé bí ó bá ṣeé ṣe. Ìbéèrè rẹ ní àkọ́kọ́, ṣùgbọ́n a kò lè ṣe ìlérí ìdáhùn ènìyàn.",
"ig":"Ọ bụrụ na ị nọ n'ihe ize ndụ ozugbo na Ghana, kpọọ 112 ugbu a. N'èzí Ghana, kpọtụrụ ọrụ mberede nke mpaghara gị. Chọọ onye ị tụkwasịrị obi ma ọ bụrụ na o kwe omume. Arịrịọ gị nwere mkpa, ma azịza mmadụ abụghị ihe e kwere nkwa.",
"sw":"Ukiwa katika hatari ya haraka nchini Ghana, piga 112 sasa. Nje ya Ghana, wasiliana na huduma za dharura za eneo lako. Wasiliana na mtu unayemwamini ikiwezekana. Ombi lako lina kipaumbele, lakini jibu la mtu halijahakikishwa.",
"ar":"إذا كنت في خطر فوري في غانا، اتصل بالرقم 112 الآن. خارج غانا، اتصل بخدمات الطوارئ المحلية. تواصل مع شخص تثق به إن أمكن. لطلبك أولوية، لكن الرد البشري غير مضمون.",
"es":"Si estás en peligro inmediato en Ghana, llama al 112 ahora. Fuera de Ghana, contacta con los servicios de emergencia locales. Acude a alguien de confianza si es posible. Tu solicitud tiene prioridad, pero no se garantiza una respuesta humana.",
"pt":"Se estiver em perigo imediato no Gana, ligue 112 agora. Fora do Gana, contacte os serviços de emergência locais. Procure alguém de confiança, se possível. O seu pedido tem prioridade, mas uma resposta humana não é garantida.",
"de":"Bei unmittelbarer Gefahr in Ghana rufen Sie jetzt 112 an. Außerhalb Ghanas kontaktieren Sie den örtlichen Notdienst. Wenden Sie sich möglichst an eine Vertrauensperson. Ihre Anfrage hat Vorrang, eine menschliche Antwort ist jedoch nicht garantiert.",
"it":"Se sei in pericolo immediato in Ghana, chiama il 112 ora. Fuori dal Ghana, contatta i servizi di emergenza locali. Cerca una persona fidata, se possibile. La tua richiesta ha priorità, ma una risposta umana non è garantita.",
"hi":"घाना में तत्काल खतरे में हों तो अभी 112 पर कॉल करें। घाना के बाहर स्थानीय आपातकालीन सेवाओं से संपर्क करें। संभव हो तो किसी भरोसेमंद व्यक्ति से संपर्क करें। आपके अनुरोध को प्राथमिकता है, लेकिन किसी व्यक्ति की प्रतिक्रिया की गारंटी नहीं है।",
"zh-CN":"如果您在加纳面临紧迫危险，请立即拨打112。在加纳以外，请联系当地紧急服务。如有可能，请联系您信任的人。您的请求会优先处理，但无法保证人工回复。",
"ru":"Если вы в непосредственной опасности в Гане, звоните 112 сейчас. За пределами Ганы обратитесь в местные экстренные службы. По возможности свяжитесь с человеком, которому доверяете. Ваш запрос имеет приоритет, но ответ человека не гарантирован.",
"uk":"Якщо вам загрожує безпосередня небезпека в Гані, телефонуйте 112 зараз. За межами Гани зверніться до місцевих екстрених служб. За можливості зв'яжіться з людиною, якій довіряєте. Ваш запит має пріоритет, але відповідь людини не гарантована.",
"bn":"ঘানায় তাৎক্ষণিক বিপদে থাকলে এখনই 112 নম্বরে কল করুন। ঘানার বাইরে স্থানীয় জরুরি পরিষেবায় যোগাযোগ করুন। সম্ভব হলে বিশ্বাসযোগ্য কারও সঙ্গে যোগাযোগ করুন। আপনার অনুরোধ অগ্রাধিকার পাবে, তবে মানুষের উত্তর নিশ্চিত নয়।",
"tr":"Gana'da acil tehlikedeyseniz şimdi 112'yi arayın. Gana dışında yerel acil servislerle iletişime geçin. Mümkünse güvendiğiniz birine ulaşın. Talebiniz önceliklidir ancak bir insanın yanıtı garanti değildir.",
"ur":"اگر آپ گھانا میں فوری خطرے میں ہیں تو ابھی 112 پر کال کریں۔ گھانا سے باہر مقامی ہنگامی خدمات سے رابطہ کریں۔ ممکن ہو تو کسی قابل اعتماد شخص سے رابطہ کریں۔ آپ کی درخواست ترجیحی ہے، لیکن انسانی جواب کی ضمانت نہیں ہے۔",
"so":"Haddii aad khatar degdeg ah ku jirto Ghana, hadda wac 112. Ghana dibaddeeda, la xiriir adeegyada gurmadka deegaanka. La xiriir qof aad ku kalsoon tahay haddii ay suurtagal tahay. Codsigaagu waa mudnaan, laakiin jawaab qof lama hubo.",
"zu":"Uma usengozini esheshayo eGhana, shayela u-112 manje. Ngaphandle kweGhana, xhumana nezinsizakalo eziphuthumayo zendawo. Xhumana nomuntu omethembayo uma kungenzeka. Isicelo sakho sibalulekile, kodwa impendulo yomuntu ayiqinisekisiwe.",
"am":"በጋና አስቸኳይ አደጋ ውስጥ ከሆኑ አሁን 112 ይደውሉ። ከጋና ውጭ የአካባቢዎን የአደጋ ጊዜ አገልግሎቶች ያነጋግሩ። ከተቻለ የሚያምኑትን ሰው ያነጋግሩ። ጥያቄዎ ቅድሚያ አለው፣ ግን የሰው ምላሽ ዋስትና የለውም።"
}
def main():
    runtime = json.loads((BASE / 'runtime.json').read_text(encoding='utf-8'))
    registry = []
    for code, native, name in ROWS:
        path = BASE / f'{code}.json'
        catalog = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
        if code == 'fr':
            for extra in ('french-completion.json', 'french-backend.json'):
                additions = json.loads((ROOT / f'scripts/{extra}').read_text(encoding='utf-8'))
                for key, value in additions.items(): catalog.setdefault(key, value)
            for key in ('AMANI','Amani','EN','FR','Ghana','Enter','Escape','Tab','WHATSAPP','WhatsApp','human','updates','forget'):
                catalog.setdefault(key, key)
        if code in CORE:
            values = CORE[code].split('|')
            assert len(values) == len(KEYS), code
            for key, value in zip(KEYS, values): catalog.setdefault(key, value)
        if code in FALLBACK: catalog.setdefault(runtime['fallback'], FALLBACK[code])
        if code in URGENT: catalog.setdefault(runtime['urgent'], URGENT[code])
        safety = json.loads((ROOT / 'scripts/language-safety.json').read_text(encoding='utf-8'))
        if code in safety:
            for key, value in zip(('Some text remains in English. Full translation is unavailable right now.', runtime['unavailable'], 'Use AI replies. My recent messages will be sent to the AI provider.'), safety[code]):
                catalog.setdefault(key, value)
        topics = json.loads((ROOT / 'scripts/topic-translations.json').read_text(encoding='utf-8'))
        if code in topics:
            assert len(topics[code]) == len(topics['keys'])
            for key, value in zip(topics['keys'], topics[code]): catalog.setdefault(key, value)
        path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        registry.append({'code':code, 'native':native, 'name':name, 'direction':'rtl' if code in ('ar','ur') else 'ltr', 'review':'Native-speaker review pending', 'coverage':'developing' if code in ('ak','ee','gaa') else 'general'})
    (BASE / 'languages.json').write_text(json.dumps(registry, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for app in ('web','moderator-dashboard'):
        dest = ROOT / f'apps/{app}/app/locales'
        dest.mkdir(parents=True, exist_ok=True)
        for path in BASE.glob('*.json'): (dest / path.name).write_bytes(path.read_bytes())
        bootstrap = {code: json.loads((BASE / f'{code}.json').read_text(encoding='utf-8')) for code, _, _ in ROWS}
        (dest / 'bootstrap.json').write_text(json.dumps(bootstrap, ensure_ascii=False), encoding='utf-8')
        if app == 'moderator-dashboard':
            (dest.parent / 'localization.tsx').write_bytes((ROOT / 'apps/web/app/localization.tsx').read_bytes())
    print(f'{len(registry)} language choices prepared; partial catalogues explicitly reported at runtime.')
if __name__ == '__main__': main()
