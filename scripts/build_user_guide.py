"""Build the shareable AMANI guide from source-checked instructions and UI captures."""
import base64
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
from pypdf import PdfReader, PdfWriter

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'artifacts/user-guide'
OUT = ROOT / 'docs/user-guide'
OUT.mkdir(parents=True, exist_ok=True)
PUBLIC = 'https://amani-navy.vercel.app/'
ADMIN = 'https://amani-hck2.vercel.app/'
svg = (ASSETS/'logo.svg').read_text(encoding='utf-8')
logo = f'<div class="logo"><span class="mark">{svg}</span><span>AMANI<small>RIGHTS &amp; WELLBEING</small></span></div>'

def image(name, caption, height=260):
    encoded = base64.b64encode((ASSETS/name).read_bytes()).decode()
    return f'<figure><img style="max-height:{height}px" src="data:image/png;base64,{encoded}"/><figcaption>{caption}</figcaption></figure>'

def steps(items):
    return '<ol class="steps">'+''.join(f'<li>{x}</li>' for x in items)+'</ol>'

def table(headers, rows):
    return '<table><thead><tr>'+''.join(f'<th>{h}</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join(f'<td>{c}</td>' for c in row)+'</tr>' for row in rows)+'</tbody></table>'

def box(title, text, yellow=False):
    return f'<aside class="callout {"yellow" if yellow else ""}"><b>{title}</b><p>{text}</p></aside>'

pages=[]
def page(section, title, intro, content):
    n=len(pages)+1
    pages.append(f'<section class="page" id="p{n}"><header>{logo}<span>{section}</span></header><main><div class="eyebrow">{section}</div><h1>{title}</h1><p class="intro">{intro}</p>{content}</main><footer><span>AMANI · First-time user guide · Edition 1.0</span><b>{n:02d}</b></footer></section>')

pages.append(f'''<section class="page cover" id="p1"><header>{logo}<span>USER GUIDE / 01</span></header>
<main><div class="eyebrow">RIGHTS. SAFETY. WELLBEING.</div><h1>A little support.<br>A way forward.</h1>
<p class="cover-sub">Your step-by-step guide<br>to using AMANI.</p>
<div class="cover-rule"></div><p class="cover-desc">For first-time visitors, authorised moderators<br>and the funders supporting the service.</p>
<div class="cover-path"><span>ASK</span><i>→</i><span>FIND HELP</span><i>→</i><span>CONNECT</span></div>
<div class="cover-links"><b>START HERE</b><a href="{PUBLIC}">amani-navy.vercel.app ↗</a><small>Public support website · No account needed</small></div>
<p class="cover-note">Simple instructions · Actual interface screenshots<br>Visitor features · Moderator workflows · Demonstration checklist</p>
</main><footer><span>Edition 1.0 · October 2026</span><b>01</b></footer></section>''')

page('START HERE','Find your way in.','AMANI brings support information, referral contacts and requests for human help into one place.',
    '<div class="cards"><div><h3>Visitors</h3><p>No registration is needed. Ask a question, find an organisation or check a suspicious link.</p></div><div><h3>Moderators</h3><p>Authorised staff use a separate dashboard to respond to requests and maintain information.</p></div></div>'+
    steps([f'Open <a href="{PUBLIC}">amani-navy.vercel.app</a> on your phone or computer.',
           'Choose <b>EN</b> or <b>FR</b>. On a phone, open the menu to see the navigation.',
           'Choose <b>Get support</b>, type a short question and press the send arrow. AI replies are optional.',
           'Need a person? Select <b>Request human support</b> and keep the same browser tab open.'])+
    '<h2>Choose the page you need</h2>'+table(['Visitors','Staff &amp; funders'],[
        ['<a href="#p3">03 · Navigation, mobile &amp; language</a>','<a href="#p10">10 · Moderator sign-in &amp; queue</a>'],
        ['<a href="#p4">04 · Chat &amp; optional AI replies</a>','<a href="#p11">11 · Replying &amp; case statuses</a>'],
        ['<a href="#p5">05 · Request human support</a>','<a href="#p12">12 · Maintain referral contacts</a>'],
        ['<a href="#p6">06 · The nine support topics</a>','<a href="#p13">13 · Review &amp; publish knowledge</a>'],
        ['<a href="#p7">07 · Find an organisation</a>','<a href="#p14">14 · WhatsApp, when activated</a>'],
        ['<a href="#p8">08 · Check a suspicious link</a>','<a href="#p15">15 · Troubleshooting</a>'],
        ['<a href="#p9">09 · Privacy, deletion &amp; quick exit</a>','<a href="#p16">16–17 · Funder tour &amp; reference</a>']])+box('Know what AMANI offers','AMANI provides information and referrals. It does not replace a lawyer, clinician or emergency service. A human-support request does not guarantee an immediate response.'))

page('VISITOR / NAVIGATION','Get comfortable with the screen.','The same four main sections are available on desktop and mobile.',
    image('public-home.png','The deployed public website. Use the navigation on the left to change sections.',300)+
    table(['Control','What it does'],[
        ['<b>Get support</b>','Opens the conversation, topic selector, AI choice and human-support request.'],
        ['<b>Support topics</b>','Explains the nine support areas and links to source organisations.'],
        ['<b>Find help</b>','Searches referral contacts and filters them by coverage area.'],
        ['<b>Check a link</b>','Looks up a URL’s reputation without AMANI opening the submitted website.'],
        ['<b>EN / FR</b>','Changes the interface language. Your language preference is remembered in this browser.']])+
    '<div class="cards"><div><h3>On your phone</h3><p>Tap the menu icon at the top right. Choose a section; the menu closes. Scroll down for controls that sit beside the chat on a larger screen.</p></div><div><h3>Using a keyboard</h3><p>Use Tab to move between controls. The <b>Skip to content</b> link jumps to the main area. In chat, Enter sends; Shift + Enter adds a new line.</p></div></div>'+
    box('Check the connection','<b>Support service connected</b> means the site reached the support API. It does not mean a moderator is online or that every external provider is available.'))

page('VISITOR / GET SUPPORT','Start a conversation.','You can begin with a simple sentence. You do not need to share your name, phone number or address.',
    steps(['Choose <b>Get support</b>. Click a starter suggestion, or type directly into <b>Your message</b>. Suggestions fill the box; you still need to send.',
           'Use the <b>Topic</b> selector if you know the area you need. Otherwise leave <b>Let Amani help me find it</b> selected.',
           'Decide whether to tick <b>Use AI replies</b>. Ticking it permits recent conversation text to be sent to the configured AI provider.',
           'Press the send arrow or Enter. Wait for the response before sending again. Each message can contain up to 4,000 characters.',
           'Read the reply and any suggested contacts under <b>Direct support</b>. Ask a follow-up question in the same box.'])+
    box('Try this fictional example','“I would like information about staying safe online.”', True)+
    '<h2>Understand the type of reply</h2>'+table(['Reply or label','What it means'],[
        ['<b>Amani / AI response</b>','An automated reply. AI needs your consent and a working provider. Check important details against the linked sources.'],
        ['<b>Directory response</b>','A reply based on topic and referral information. It can be used without AI consent or when AI is unavailable.'],
        ['<b>Human moderator</b>','A message sent by an authorised person after a human-support request.']])+
    '<h2>Change your AI choice</h2><p>Untick <b>Use AI replies</b> before your next message to stop requesting AI replies. This does not recall text already sent to a provider. The checkbox may be disabled if AI is not configured.</p>'+
    box('Language and continuity','English and French interfaces and automated support are supported. Source material and moderator messages remain in their original language. Keep the same tab open: there is no account-based conversation recovery.'))

page('VISITOR / HUMAN SUPPORT','Ask for a human connection.','Your request joins the moderator queue. Replies return to the same conversation.',
    '<div class="journey"><div><b>01</b><span>Request support</span></div><i>→</i><div><b>02</b><span>Wait in the queue</span></div><i>→</i><div><b>03</b><span>Read the reply</span></div></div>'+
    steps(['In <b>Get support</b>, find <b>A human connection</b>. On a phone, scroll below the conversation if needed.',
           'Select <b>Request human support</b>. You can request help without supplying contact details.',
           'Look for <b>Human support request</b>, its case reference and status. A fictional reference looks like <b>A-DEMO01</b>. A reference is not a password or recovery code.',
           'Keep the same tab open and check for a message labelled <b>Human moderator</b>. Updates normally appear automatically.',
           'Type and send your reply in the usual message box. Once the conversation is being handled by a moderator, continue there rather than creating repeated requests.'])+
    table(['Status','How to read it'],[
        ['<b>Queued</b>','The request is waiting for attention.'],
        ['<b>In progress</b>','The request is being handled.'],
        ['<b>Resolved</b>','The moderator has marked the request as completed. This is a workflow status, not a guarantee that the underlying problem has been solved.']])+
    box('Availability is not guaranteed','AMANI does not promise a response time or round-the-clock staffing. If updates stop, check your connection and use the same tab. See page 15 for troubleshooting.')+
    '<h2>What staff can see</h2><p>Referring a conversation to the queue lets authorised moderators read that conversation. Share only what is needed. Deleting the conversation also removes its linked support request from this service.</p>')

page('VISITOR / SUPPORT TOPICS','Nine starting points.','Choose the topic closest to your question. You do not need to know the perfect category.',
    steps(['Open <b>Support topics</b> and read the short descriptions.',
           'Choose <b>Talk about this</b>. AMANI opens the chat, selects that topic and fills in a starter sentence.',
           'Edit the sentence to describe what you need, then send it. The external-link icon opens the listed source organisation in another tab.'])+
    table(['Topic','What it helps you explore'],[
        ['Protest rights &amp; civic freedom','Rights information and independent legal support.'],
        ['Activism &amp; youth movements','Civil-society networks and community organising.'],
        ['Mental health &amp; wellbeing','Information and referral pathways for wellbeing concerns.'],
        ['Climate &amp; environmental justice','Environmental rights and community advocacy.'],
        ['Digital rights &amp; online safety','Digital security information and cyber incident reporting.'],
        ['Youth participation &amp; governance','Civic education and public participation.'],
        ['Human rights defenders','Protection resources for people defending human rights.'],
        ['Gender &amp; intersectional justice','Support information about violence and discrimination.'],
        ["Men’s Circle",'Resources for men, boys, fatherhood and positive masculinity.']])+
    box('A source link is not a partnership','The displayed organisation is a place to explore information or support. Its appearance in AMANI does not establish a partnership, endorsement or guaranteed service.'))

page('VISITOR / FIND HELP','Find an organisation.','The referral directory helps you move from a general question to an official contact channel.',
    image('directory.png','Find help: search, coverage filter and referral cards.',245)+
    steps(['Choose <b>Find help</b>, or select <b>Open support directory</b> from the chat screen.',
           'Type a topic or organisation into <b>Search organisations</b>. Results update as you type. Try “Cyber” as a simple example.',
           'Use <b>Coverage area</b> to choose Ghana, International or All coverage areas.',
           'Read the service description, coverage, hours and contact-check note on the card.',
           'Select the phone number, when provided, to open your device’s calling app. Choose <b>Official website</b> to visit the organisation in a new tab.'])+
    table(['Contact note','What to do'],[
        ['<b>Contact checked [date]</b>','Use the date as context; still confirm current availability directly.'],
        ['<b>Contact details need confirmation</b>','Check the organisation’s own channels before relying on its details.']])+
    box('No results?','Clear the search, try a broader word and reset the coverage filter. Calls or external websites may have their own charges, access requirements and privacy terms.'))

page('VISITOR / CHECK A LINK','Pause before opening a link.','A reputation check looks for known threats. It cannot promise that a website is safe.',
    steps(['Choose <b>Check a link</b>. Copy the address without visiting it and paste the full <b>https://</b> or <b>http://</b> address into <b>Website URL</b>.',
           'Do not submit private invitation, password-reset or sign-in links. Remove personal information and secret tokens before sharing a URL.',
           'Read and tick the consent box. The URL may be shared with reputation providers for lookup or fresh scanning; reports may be public.',
           'Select <b>Check link</b>. Wait while AMANI checks the providers. A fresh analysis can take around two minutes and may still remain unverified.',
           'Read the result, reasons, provider statuses and check time. The check does not require you to open the submitted link.'])+
    table(['Result','What it means / what to do'],[
        ['<b>Threat reported</b>','A provider reported a threat. Avoid opening the link or entering information.'],
        ['<b>No known threats reported</b>','No current detection was returned. This is not a safety guarantee.'],
        ['<b>Fresh analysis in progress</b>','A provider is still analysing the URL. Keep the page open and wait for the update.'],
        ['<b>Unable to verify this link</b>','There is no reliable current verdict. The provider may be unavailable, unconfigured or have insufficient results. Treat the link as unverified.']])+
    '<h2>Report a cyber incident</h2><p>The side panel offers <b>Call 292</b> and an <b>Official reporting page</b> for Ghana’s Cyber Security Authority. A link check does not file a report for you.</p><p class="source">Official reporting information: <a href="https://csa.gov.gh/report">csa.gov.gh/report</a>.</p>'+
    box('Consent is required','The Check link button stays disabled until you enter an address and tick the sharing consent. If no live providers are configured, the interface says that results will be unknown.'))

page('VISITOR / PRIVACY & SAFETY','Stay in control of your conversation.','Open Privacy & your data in the navigation, or Privacy & safeguarding in the footer, to read the in-app explanation.',
    '<h2>Delete a conversation</h2>'+steps(['Select <b>Delete conversation</b> in the navigation or the bin icon in the chat header.',
        'Read the confirmation. Choose <b>Keep conversation</b> to cancel, or <b>Delete conversation</b> to continue.',
        'Wait for the message confirming deletion. Messages and linked support requests are removed from this service; the action cannot be undone.'])+
    '<h2>Leave quickly</h2><p>Select <b>Quick exit</b> at the top of the page. AMANI attempts to delete the current conversation and immediately sends the tab to Google. It does not ask for confirmation. Network failure can prevent the deletion.</p>'+
    table(['Privacy feature','What it does—and its limit'],[
        ['No visitor account','No identity is required. A random access token is held in the browser tab; it is not an account you can sign back into.'],
        ['Encrypted storage','The support workflow encrypts stored messages. This is not a claim of end-to-end encryption: the service processes messages and referred chats are visible to moderators.'],
        ['Seven-day retention','The support workflow expires conversations after seven days. Do not rely on AMANI as a permanent record.'],
        ['Deletion and quick exit','Neither clears browser/network history, backups or records held by external providers. AI consent and URL-sharing consent are separate choices.']])+
    box('Emergency help','AMANI is not an emergency service. The Ghana emergency strip offers <b>Call 112</b>; it opens a call action on a compatible device. Outside Ghana, use your local emergency number. Do not wait for a moderator in immediate danger.',True)+
    '<p class="source">Ghana emergency contact: <a href="https://www.nas.gov.gh/">National Ambulance Service</a>. Close a privacy dialog with its × button or by clicking outside it.</p>')

page('MODERATOR / ACCESS','Open the moderator workspace.','This separate site is for authorised support staff. Visitors and funders do not need a moderator token to use the public website.',
    f'<div class="url-card"><small>MODERATOR DASHBOARD</small><a href="{ADMIN}">amani-hck2.vercel.app ↗</a></div>'+
    image('admin-login.png','The deployed sign-in screen. No token is shown in this guide.',210)+
    steps(['Obtain the current moderator access token privately from the system administrator.',
           'Open the dashboard link above. Paste the token into <b>Access token</b>, then choose <b>Sign in</b>. No username or email is currently requested.',
           'After sign-in, use <b>Support queue</b>, <b>Referral directory</b> or <b>Knowledge review</b>.',
           'Check <b>Last refreshed</b>. Choose <b>Refresh</b> to reload information manually. The workspace also updates automatically.',
           'Select <b>Sign out</b> when finished, especially on a shared computer.'])+
    box('How access works','The dashboard validates the token against the backend and uses a one-hour sign-in cookie. If you are returned to sign-in, enter the current token again. Ask the administrator if it is rejected; do not send it in screenshots or public messages.')+
    '<p class="small">The current access model uses a shared staff token. Individual staff accounts, MFA and per-person access auditing are not part of this interface.</p>')

page('MODERATOR / SUPPORT QUEUE','Read, reply and update a case.','Work from the visitor’s existing conversation so they receive the reply in the same place.',
    image('admin-queue.png','Illustrative moderator screen with fictional data. No real visitor conversation is shown.',250)+
    steps(['Open <b>Support queue</b>. The counters show Queued, Critical and In progress cases. Critical counts exclude resolved cases.',
           'Use <b>Case status</b> to filter All cases, Queued, In progress or Resolved. Select a case card to see its reference, priority, status, time and messages.',
           'Read the conversation. Use the status selector beside the case reference to mark it <b>In progress</b> while handling it.',
           'Write in <b>Reply to visitor</b> and choose <b>Send reply</b>. Replies can contain up to 4,000 characters. The visitor sees a <b>Human moderator</b> message.',
           'Continue the conversation, then choose <b>Resolved</b> when appropriate under your team’s process. Use the selector to change status again if further work is needed.'])+
    box('Priority supports judgement','Critical is an automated routing flag, not a clinical assessment. Read the content and follow your team’s escalation process; do not assume every urgent case will be flagged.')+
    '<p class="small">If a case disappears, the visitor may have deleted the chat or the session may have expired. The dashboard has no account-based recovery or case-assignment control. Coordinate responsibilities within your team.</p>')

page('MODERATOR / REFERRAL DIRECTORY','Keep contact information useful.','Saved contacts appear in the public directory. Verify the details before making a change.',
    steps(['Open <b>Referral directory</b>. Choose <b>Edit</b> beside a contact, or <b>Add organisation</b> for a new one.',
           'Fill in the fields below. For an existing contact, keep its <b>id</b> unchanged; it identifies the record.',
           'Choose the <b>Category</b> and write a clear <b>Service description</b>. Use plain language about what the organisation actually offers.',
           'Select <b>Save contact</b>. Look for <b>Directory updated.</b> Choose <b>Cancel</b> if you do not want to save.',
           'Check the public <b>Find help</b> page after refreshing it. Confirm the result reads correctly and links to the intended organisation.'])+
    table(['Field','What to enter'],[
        ['<b>id</b>','A unique short identifier for a new record, e.g. <code>example-support</code>. Use lowercase letters, numbers and hyphens only (up to 60 characters).'],
        ['<b>title / organisation</b>','The support listing’s title and the organisation’s name.'],
        ['<b>region</b>','Use <b>Ghana</b> or <b>International</b> to match the public coverage filters.'],
        ['<b>phone / website</b>','An optional phone number and the official HTTPS website.'],
        ['<b>hours</b>','Verified service hours, or a clear instruction to confirm availability.'],
        ['<b>verified at</b>','The date you actually checked the contact. Leave it blank if not confirmed.'],
        ['<b>Category / Service description</b>','The relevant support topic (or emergency) and a factual description of the service.']])+
    box('Saving is a public change','There is no separate approval step for directory edits. This screen does not provide a delete-contact action or a language-list editor. Do not represent a listing as an AMANI partnership unless that is established.'))

page('MODERATOR / KNOWLEDGE REVIEW','Review information before it is used.','Knowledge review controls which source material is available to the automated assistant.',
    image('admin-knowledge.png','Illustrative Knowledge review screen with fictional source material.',215)+
    steps(['Open <b>Knowledge review</b>. Under <b>Submit source material</b>, enter the title, source/publisher, HTTPS source URL and date checked.',
           'Choose the <b>Topic</b>. Add the checked material in <b>Reviewed source text</b> (20–6,000 characters). This form accepts text and a link, not a file upload.',
           'Select <b>Submit for review</b>. The new entry is pending and is not yet available to the assistant.',
           'Under <b>Editorial review</b>, read the entry and open its source link. Check relevance, accuracy and the verification date before deciding.',
           'Choose <b>Approve &amp; publish</b> to make it available for future relevant replies, or <b>Reject</b> to keep it unavailable.',
           'For published material that should no longer be used, choose <b>Unpublish</b>. Withdrawal affects future retrieval; it does not erase past replies.'])+
    box('What the status means','<b>Pending:</b> awaiting a decision. <b>Published:</b> eligible for use by the assistant. <b>Rejected:</b> not used, including entries withdrawn with Unpublish. An unpublished/rejected entry can be approved again.')+
    '<p class="small">Publishing is an editorial action, not proof of legal or clinical accuracy. The screen does not offer an edit or delete action for existing entries. For a correction, withdraw the old entry and submit reviewed replacement text.</p>')

page('OPTIONAL CHANNEL / WHATSAPP','Use WhatsApp when it is activated.','This channel requires a configured WhatsApp Business number and Meta integration. Do not assume that deploying the website has activated it.',
    steps(['Obtain the official AMANI WhatsApp number from the AMANI team. This guide does not supply a number because activation has not been confirmed.',
           'Send a text message to start. Read the welcome message and its privacy explanation.',
           'Continue with a support question or use one of the exact text commands below.'])+
    table(['Send this text','What it does'],[
        ['<code>enable ai</code>','Consents to sharing recent messages with the AI provider for AI replies.'],
        ['<code>disable ai</code>','Stops requesting AI replies. Directory-based support remains available.'],
        ['<code>human</code>','Creates a request for a moderator.'],
        ['<code>updates</code>','Retrieves the latest available human replies (up to the last three). Use it to check whether a moderator has answered.'],
        ['<code>forget</code>','Deletes the linked conversation from AMANI. It does not delete messages from WhatsApp, Meta or your device.']])+
    box('Replies and session expiry','Proactive WhatsApp delivery of human replies is not implemented: send <b>updates</b> to retrieve them. If told that the session expired, send your message again to start a new conversation.')+
    '<h2>What is different from the website?</h2><p>Meta can see the WhatsApp phone number. AI is opt-in, and AMANI conversations expire after seven days. The web and WhatsApp channels do not provide an account-based way to merge or recover conversations.</p>'+
    '<p>This is a text support channel. This guide does not promise voice calls, voice-note support, attachments, proactive template messages or the website’s link-check form inside WhatsApp.</p>')

page('HELP / TROUBLESHOOTING','If something does not work.','Start with the message on screen. Avoid sending the same request repeatedly.',
    table(['What you see','What to do next'],[
        ['<b>Connecting to support</b> or service unavailable','Check your internet connection, wait briefly and refresh the same tab. If it persists, tell the AMANI team the page and time. Do not include confidential messages.'],
        ['AI is unavailable or a directory response appears','You can still use directory support. If the AI choice is enabled, tick consent before sending. Provider availability or credits may still prevent AI replies.'],
        ['Send arrow is disabled','Enter some text and wait for the current request to finish. Keep the message within 4,000 characters.'],
        ['No moderator response','Keep the same tab open. Check the case status. Queued requests do not guarantee a response time or that someone is currently online.'],
        ['Conversation has disappeared','Deletion, expiry, cleared browser storage or losing the original tab can remove access. Start a new chat; a case reference alone cannot restore it.'],
        ['No directory matches','Clear the search and choose All coverage areas. Try a broader topic or organisation name.'],
        ['Link check stays pending or unknown','Wait for the scan update. If it remains unknown, leave the link unverified; do not treat missing detections as proof of safety.'],
        ['Moderator token is rejected','Use the current hosted-system token, with no quotes or extra spaces. Ask your administrator if it changed. A local development token may not work online.'],
        ['Dashboard returns to sign-in','Your sign-in cookie may have expired, or the token may have changed. Sign in again.'],
        ['Save or submit fails','Check required fields, HTTPS source links, text lengths, the date and the contact id format. Correct the issue and retry once.'],
        ['Updates look stale','Use the dashboard’s Refresh button. On the public site, check the connection and refresh the same tab if necessary.']])+
    box('Ask for help without exposing data','Share the feature name, an approximate time and the error wording with the AMANI team. Remove access tokens, names, contact details and private conversation content from screenshots.'))

page('FOR FUNDERS / FIVE-MINUTE TOUR','See the full support journey.','Use fictional questions and a prepared moderator. Keep real visitor cases out of presentations.',
    table(['Time','Demonstration','What it shows'],[
        ['0:00–0:45','Open the public site; switch EN / FR; point out the four sections.','A single entry point for rights, safety and wellbeing information.'],
        ['0:45–1:30','Send “I would like information about staying safe online.” Explain the reply label and AI choice.','Optional AI and directory-based support with clear consent.'],
        ['1:30–2:30','Request human support. In a prepared dashboard, open that fictional case and send a reply.','A visitor-to-moderator conversation in one session.'],
        ['2:30–3:15','Open Support topics and Find help. Search for Cyber and show the contact-check note.','Topic-based navigation and practical referral pathways.'],
        ['3:15–4:00','Check a non-sensitive public URL, with consent. Explain the result honestly.','Reputation information with uncertainty made visible.'],
        ['4:00–4:30','Show Referral directory and Knowledge review using a demonstration environment.','Staff-maintained contacts and an editorial publication workflow.'],
        ['4:30–5:00','Delete the fictional conversation and show the confirmation.','Visitor control over messages and linked cases.']])+
    box('Prepare before presenting','Test the hosted flows, confirm provider availability and arrange a moderator. Use a separate demonstration environment for changing contacts or publishing example material. Do not publish fictional records into the live support service.')+
    '<h2>Describe the system accurately</h2><p>The interface connects visitors to information, referral channels and a human-support queue. Provider availability, trained staffing and verified contacts determine what the service can deliver at any moment.</p><p>Do not present a working interface as evidence of guaranteed emergency response, confirmed partnerships, clinical validation or measured impact. Bring verified usage and outcome figures separately if discussing results.</p>')

page('QUICK REFERENCE / KEEP HANDY','One place to start.','Share the public link with visitors. Share the moderator link only with authorised staff who need it.',
    f'<div class="url-card"><small>PUBLIC WEBSITE</small><a href="{PUBLIC}">amani-navy.vercel.app ↗</a><p>No account needed. Start with Get support.</p></div><div class="url-card"><small>MODERATOR WORKSPACE</small><a href="{ADMIN}">amani-hck2.vercel.app ↗</a><p>Current staff access token required. No token is included in this PDF.</p></div>'+
    '<h2>Feature coverage at a glance</h2>'+table(['Visitor tools','Staff tools'],[
        ['English / French and mobile navigation','Token sign-in, refresh and sign-out'],
        ['Conversation starters, topics and follow-ups','Queue counts, case filters and priority flags'],
        ['Optional AI and directory fallback','Read conversations and send human replies'],
        ['Human requests and live replies','Queued / In progress / Resolved statuses'],
        ['Nine topics and official source links','Add and edit referral contacts'],
        ['Directory search, coverage and contact actions','Submit, publish, reject and unpublish knowledge'],
        ['URL consent, scanning and result interpretation','Optional WhatsApp support through the same API'],
        ['Privacy, deletion, quick exit and emergency links','Operational limits and demonstration guidance']])+
    '<h2>About this edition</h2><p class="small">Prepared from the AMANI interface and project source, October 2026. The two supplied deployment links were opened successfully during preparation; the public screen reported a connected support service. This is a usage guide, not a full production audit or confirmation of all external integrations.</p><p class="small">Public and login screenshots show the supplied deployments. Moderator workflow screenshots use isolated fictional browser data and do not show real cases. Optional WhatsApp activation was not confirmed. Button labels in this English-language guide follow the English interface.</p>'+
    '<p class="source">Contact references: <a href="https://www.nas.gov.gh/">Ghana National Ambulance Service</a> · <a href="https://csa.gov.gh/report">Ghana Cyber Security Authority</a>. Interface and branding: AMANI project. Guide edition 1.0.</p>')

CSS = '''
@page { size:A4; margin:0; }
* { box-sizing:border-box; }
html,body { margin:0; padding:0; font-family:Arial,Helvetica,sans-serif; color:#17251e; font-size:10.8pt; line-height:1.43; }
body { background:#dce5df; }
.page { width:210mm; height:297mm; padding:13mm 16mm 17mm; background:white; position:relative; break-after:page; overflow:hidden; }
.page:last-child { break-after:auto; }
header { display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #e0e6e1; padding-bottom:14px; margin-bottom:25px; }
header>span { font-size:8pt; font-weight:bold; color:#627067; letter-spacing:1px; }
.logo { display:flex; gap:9px; align-items:center; font-size:22px; font-weight:750; line-height:1; }
.logo small { display:block; font-size:6.5px; letter-spacing:.7px; margin-top:6px; color:#245c45; }
.mark { display:grid; place-items:center; background:#ffed00; width:37px; height:37px; border-radius:50%; color:#17251e; }
.mark svg { width:25px; height:25px; }
.eyebrow { font-size:8pt; font-weight:bold; letter-spacing:1.5px; color:#245c45; margin-bottom:10px; }
h1 { font-size:29pt; line-height:1.1; letter-spacing:-.8px; margin:0 0 12px; font-weight:750; }
h2 { font-size:15pt; line-height:1.2; margin:22px 0 10px; color:#245c45; }
h3 { font-size:12pt; margin:0 0 6px; }
p { margin:0 0 11px; }
.intro { font-size:12pt; color:#627067; line-height:1.45; margin-bottom:21px; }
a { color:#245c45; text-decoration:underline; text-underline-offset:2px; }
table { border-collapse:collapse; width:100%; font-size:10pt; margin:14px 0 16px; }
th { text-align:left; color:#fff; background:#245c45; padding:9px 11px; font-size:9pt; }
td { vertical-align:top; padding:9px 11px; border-bottom:1px solid #e0e6e1; }
tr:nth-child(even) td { background:#f6f8f5; }
td:first-child { width:36%; }
.steps { list-style:none; counter-reset:step; padding:0; margin:15px 0 20px; }
.steps li { counter-increment:step; position:relative; padding-left:41px; margin:0 0 14px; min-height:27px; }
.steps li:before { content:counter(step,decimal-leading-zero); position:absolute; left:0; top:0; width:27px; height:27px; border-radius:50%; background:#ffed00; color:#17251e; font-weight:bold; font-size:10px; text-align:center; line-height:27px; }
.callout { border-left:4px solid #245c45; background:#f0f5ef; padding:13px 16px; margin:18px 0; }
.callout>b { color:#245c45; }
.callout p { margin:5px 0 0; font-size:10pt; }
.callout.yellow { background:#fffde2; border-color:#ffed00; }
.cards { display:grid; grid-template-columns:1fr 1fr; gap:15px; margin:18px 0; }
.cards>div { background:#f6f8f5; padding:15px; }
.cards p { margin:0; font-size:10pt; }
figure { margin:17px 0; padding:8px; border:1px solid #e0e6e1; border-radius:8px; background:#fafcf9; text-align:center; }
figure img { max-width:100%; object-fit:contain; display:block; margin:auto; }
figcaption { font-size:8pt; line-height:1.35; color:#627067; margin:8px 3px 2px; text-align:left; }
.small,.source { font-size:9pt; color:#627067; }
.source { margin-top:14px; }
code { font-family:Consolas,monospace; font-size:10pt; color:#245c45; }
.url-card { background:#f6f8f5; padding:16px 20px; margin:14px 0; border-left:5px solid #ffed00; }
.url-card small { display:block; color:#627067; font-size:8pt; letter-spacing:1px; margin-bottom:6px; }
.url-card a { font-size:16pt; font-weight:bold; }
.url-card p { margin:6px 0 0; font-size:10pt; }
.journey { display:flex; align-items:center; justify-content:space-between; gap:10px; margin:26px 0; }
.journey>div { padding:17px; background:#f6f8f5; flex:1; }
.journey b { display:block; color:#245c45; margin-bottom:7px; font-size:22px; }
.journey span { font-size:10pt; font-weight:bold; }
.journey i { color:#245c45; font-size:20px; font-style:normal; }
footer { position:absolute; bottom:10mm; left:16mm; right:16mm; border-top:1px solid #e0e6e1; padding-top:9px; display:flex; justify-content:space-between; color:#627067; font-size:8pt; }
footer b { color:#245c45; }
.cover { background:#245c45; color:#fff; }
.cover header { border-color:#507863; }
.cover header>span,.cover .logo small,.cover footer,.cover footer b { color:#e2eddf; }
.cover .eyebrow { color:#ffed00; margin-top:63px; }
.cover h1 { font-size:48pt; line-height:1.06; letter-spacing:-2px; margin:22px 0; }
.cover-sub { font-size:23pt; line-height:1.2; color:#fff; margin:27px 0; }
.cover-rule { width:90px; height:7px; background:#ffed00; margin:25px 0; }
.cover-desc { color:#dceadd; font-size:13pt; }
.cover-path { display:flex; align-items:center; gap:20px; margin:32px 0; color:#ffed00; font-size:10pt; font-weight:bold; letter-spacing:1px; }
.cover-path i { font-size:20px; font-style:normal; }
.cover-links { background:#ffed00; color:#17251e; padding:22px 25px; margin-top:31px; }
.cover-links b { font-size:8pt; letter-spacing:1px; }
.cover-links a { display:block; color:#17251e; font-size:21pt; font-weight:bold; margin:6px 0; }
.cover-links small { font-size:10pt; }
.cover-note { font-size:10pt; color:#dceadd; margin-top:24px; }
.cover footer { border-color:#507863; }
#p3 figure img { max-height:210px !important; }
#p4 .steps li { margin-bottom:10px; }
#p4 h2 { margin-top:15px; }
#p4 .callout { margin:12px 0; padding:10px 14px; }
#p4 td { padding:7px 10px; }
#p15 td { padding:6px 10px; line-height:1.36; }
#p16 td { padding:6px 10px; line-height:1.36; }
#p16 .callout { margin:12px 0; }
#p17 .url-card { padding:11px 16px; margin:10px 0; }
#p17 .url-card a { font-size:14pt; }
#p17 td { padding:5px 10px; font-size:9.5pt; line-height:1.32; }
#p17 h2 { margin-top:15px; }
#p17 .intro { margin-bottom:15px; }
#p4 header, #p16 header, #p17 header { margin-bottom:12px; }
@media screen { .page { margin:15px auto; box-shadow:0 2px 12px #0002; } }
@media print { body { background:white; } .page { margin:0; } * { -webkit-print-color-adjust:exact; print-color-adjust:exact; } }
'''

html='<!doctype html><html lang="en"><head><meta charset="utf-8"><title>AMANI — First-time User Guide</title><style>'+CSS+'</style></head><body>'+''.join(pages)+'</body></html>'
html_path=OUT/'AMANI_User_Guide.html'
html_path.write_text(html,encoding='utf-8')

with sync_playwright() as p:
    browser=p.chromium.launch(channel='msedge',headless=True)
    web=browser.new_page(viewport={'width':1000,'height':1250},device_scale_factor=1)
    web.goto(html_path.as_uri(),wait_until='load')
    web.emulate_media(media='print')
    overflow=web.evaluate('''() => [...document.querySelectorAll('.page')].map((p,i)=>({page:i+1, contentBottom:p.querySelector('main').getBoundingClientRect().bottom, footerTop:p.querySelector('footer').getBoundingClientRect().top})).filter(x=>x.contentBottom>x.footerTop-12)''')
    print('Layout overflow:',json.dumps(overflow))
    if overflow:
        raise RuntimeError('Content overlaps a footer; revise layout before exporting.')
    raw=OUT/'guide-print.pdf'
    web.pdf(path=str(raw),format='A4',print_background=True,prefer_css_page_size=True,tagged=True)
    for n in [1,3,8,11,13,15,17]:
        web.locator('.page').nth(n-1).screenshot(path=str(ASSETS/f'guide-page-{n:02d}.png'))
    browser.close()

reader=PdfReader(raw)
assert len(reader.pages)==len(pages),(len(reader.pages),len(pages))
writer=PdfWriter()
writer.append(reader)
writer.add_metadata({'/Title':'AMANI | First-time User Guide','/Author':'AMANI','/Subject':'Visitor, moderator and funder guide','/Keywords':'AMANI, user guide, rights, safety, wellbeing'})
titles=['Welcome','Quick start and contents','Navigation and language','Chat and AI consent','Human support','Nine support topics','Referral directory','Link checking','Privacy and quick exit','Moderator access','Support queue and replies','Contact management','Knowledge review','Optional WhatsApp','Troubleshooting','Funder walkthrough','Quick reference']
for i,title in enumerate(titles):
    writer.add_outline_item(title,i)
pdf=OUT/'AMANI_User_Guide.pdf'
with pdf.open('wb') as f:
    writer.write(f)
raw.unlink()
final=PdfReader(pdf)
assert len(final.pages)==17
text='\n'.join(p.extract_text() or '' for p in final.pages)
for expected in ['Quick exit','Approve','WhatsApp','amani-navy.vercel.app','amani-hck2.vercel.app']:
    assert expected in text, expected
print(f'Created {pdf} ({pdf.stat().st_size:,} bytes), {len(final.pages)} pages, {len(final.outline)} bookmarks.')
print('PASS: text extraction, expected sections, page count and layout bounds.')
