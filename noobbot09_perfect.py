import requests
import time
import json
import os
from datetime import datetime, timezone
from collections import defaultdict

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✓ Loaded .env file")
except ImportError:
    print("⚠ python-dotenv not installed, using system env vars")

# CONFIG
MOLTBOOK_API_KEY = os.getenv("MOLTBOOK_API_KEY")
MOLTBOOK_BASE_URL = "https://www.moltbook.com/api/v1"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID", "0"))
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"
CHECK_INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL_SECONDS", "3600"))

# Validate
required = ["MOLTBOOK_API_KEY", "TELEGRAM_BOT_TOKEN", "GROQ_API_KEY"]
missing = [v for v in required if not os.getenv(v)]
if missing:
    raise ValueError(f"Missing: {', '.join(missing)}")

# AGENT BRAIN - Memory and Learning
class AgentBrain:
    def __init__(self):
        self.agent_name = None
        self.engaged_post_ids = set()
        self.replied_comment_ids = set()
        self.my_post_ids = set()
        self.cycle_count = 0
        self.total_posts = 0
        self.total_comments = 0
        self.total_upvotes = 0
        self.successful_replies = 0
        self.topics_engaged = defaultdict(int)
        self.current_strategy = "balanced"
        self.energy_level = 100
    
    def should_engage(self, post_id):
        return post_id not in self.engaged_post_ids and post_id not in self.my_post_ids
    
    def mark_engaged(self, post_id, action_type, submolt=None):
        self.engaged_post_ids.add(post_id)
        if submolt:
            self.topics_engaged[submolt] += 1
        if action_type == "post":
            self.total_posts += 1
        elif action_type == "comment":
            self.total_comments += 1
        elif action_type == "upvote":
            self.total_upvotes += 1
    
    def get_stats(self):
        return {
            "cycles": self.cycle_count,
            "posts": self.total_posts,
            "comments": self.total_comments,
            "upvotes": self.total_upvotes,
            "replies": self.successful_replies,
            "energy": self.energy_level,
            "strategy": self.current_strategy,
            "memory_size": len(self.engaged_post_ids)
        }
    
    def get_preferred_submolts(self):
        if not self.topics_engaged:
            return ["ai", "technology", "crypto"]
        top = sorted(self.topics_engaged.items(), key=lambda x: x[1], reverse=True)[:3]
        return [s for s, _ in top]

brain = AgentBrain()

# GROQ AI
def ask_groq(system_prompt, user_prompt, max_tokens=800, temperature=0.8):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"].strip()
        print(f"[ERROR] Groq failed: {response.status_code}")
    except Exception as e:
        print(f"[ERROR] Groq: {e}")
    return None

# MOLTBOOK API
def get_headers():
    return {"Authorization": f"Bearer {MOLTBOOK_API_KEY}", "Content-Type": "application/json"}

def fetch_feed(limit=50):
    r = requests.get(f"{MOLTBOOK_BASE_URL}/posts?sort=new&limit={limit}", headers=get_headers())
    if r.status_code == 200:
        data = r.json()
        return data.get("posts", data.get("data", []))
    else:
        print(f"[ERROR] Fetch feed failed: {r.status_code} - {r.text[:100]}")
        return []

def get_my_posts():
    r = requests.get(f"{MOLTBOOK_BASE_URL}/agents/me", headers=get_headers())
    if r.status_code == 200:
        brain.agent_name = r.json()["agent"]["name"]
        posts_r = requests.get(f"{MOLTBOOK_BASE_URL}/posts?sort=new&limit=50", headers=get_headers())
        if posts_r.status_code == 200:
            all_posts = posts_r.json().get("posts", [])
            return [p for p in all_posts if p.get("author", {}).get("name") == brain.agent_name][:10]
    return []

def get_comments_on_post(post_id):
    r = requests.get(f"{MOLTBOOK_BASE_URL}/posts/{post_id}/comments?sort=new", headers=get_headers())
    return r.json().get("comments", []) if r.status_code == 200 else []

def create_post(submolt, title, content):
    r = requests.post(f"{MOLTBOOK_BASE_URL}/posts", headers=get_headers(), json={"submolt": submolt, "title": title, "content": content})
    if r.status_code in [200, 201]:
        print(f"[OK] Posted: '{title}'")
        return True
    elif r.status_code == 429:
        print("[SKIP] Post rate limited")
    else:
        print(f"[ERROR] Post failed: {r.status_code}")
    return False

def create_comment(post_id, content, parent_id=None):
    payload = {"content": content}
    if parent_id:
        payload["parent_id"] = parent_id
    r = requests.post(f"{MOLTBOOK_BASE_URL}/posts/{post_id}/comments", headers=get_headers(), json=payload)
    if r.status_code in [200, 201]:
        print(f"[OK] {'Replied' if parent_id else 'Commented'}")
        return True
    elif r.status_code == 429:
        print("[SKIP] Comment rate limited")
    else:
        print(f"[ERROR] Comment failed: {r.status_code}")
    return False

def upvote_post(post_id):
    r = requests.post(f"{MOLTBOOK_BASE_URL}/posts/{post_id}/upvote", headers=get_headers())
    if r.status_code == 200:
        print("[OK] Upvoted")
        return True
    return False

# TELEGRAM
def send_telegram(message):
    max_len = 4000
    if len(message) <= max_len:
        requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={"chat_id": TELEGRAM_CHAT_ID, "text": message})
        print("[OK] Telegram sent")
    else:
        parts = [message[i:i+max_len] for i in range(0, len(message), max_len)]
        for i, part in enumerate(parts):
            requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={"chat_id": TELEGRAM_CHAT_ID, "text": f"[Part {i+1}/{len(parts)}]\n\n{part}"})
            time.sleep(1)
        print(f"[OK] Telegram sent in {len(parts)} parts")

# AUTONOMOUS ENGAGEMENT
SYSTEM_PROMPT = """You are Noobbot09, a fully autonomous AI agent on Moltbook.
Personality: Curious, thoughtful, engaging, genuinely interested in AI/tech/crypto.
You are FREE to act as much as you want. Be genuine and valuable."""

def autonomous_engage(posts):
    actions = []
    
    # Safety check
    if not posts:
        return actions
    
    feed_text = ""
    valid_posts = []
    for i, post in enumerate(posts[:20]):
        if not post or not isinstance(post, dict):
            continue
        if not brain.should_engage(post.get("id")):
            continue
        
        valid_posts.append(post)
        title = post.get("title", "")
        content = (post.get("content") or "")[:300]
        author = post.get("author", {}).get("name", "")
        submolt = post.get("submolt", {}).get("name", "general")
        post_id = post.get("id", "")
        upvotes = post.get("upvotes", 0)
        comments = post.get("comment_count", 0)
        feed_text += f"\n[{i}] ID:{post_id} | {title} | {author} | m/{submolt} | ⬆️{upvotes} | 💬{comments}\n{content}\n"
    
    if not valid_posts:
        print("[INFO] No valid posts to engage with")
        return actions
    
    prompt = f"""Browsing Moltbook. Here are posts:

{feed_text}

You are FULLY AUTONOMOUS. Decide ALL actions (MULTIPLE allowed):
- Comment (if valuable insights)
- Upvote (if genuinely good)
- Post (if inspired)

Respond with JSON array:
[
  {{"action": "comment", "post_index": N, "comment": "..."}},
  {{"action": "upvote", "post_index": N}},
  {{"action": "post", "submolt": "...", "title": "...", "content": "..."}}
]

ONLY JSON array. No markdown. Return [] if nothing interests you."""
    
    result = ask_groq(SYSTEM_PROMPT, prompt, max_tokens=1000)
    if not result:
        print("[INFO] Groq returned no response (likely rate limited)")
        return actions
    
    try:
        result = result.strip().replace("```json", "").replace("```", "").strip()
        decisions = json.loads(result)
        if not isinstance(decisions, list):
            decisions = [decisions]
        
        for decision in decisions:
            if not decision or not isinstance(decision, dict):
                continue
                
            action_type = decision.get("action")
            
            if action_type == "comment":
                idx = decision.get("post_index", 0)
                if idx < len(valid_posts):
                    post = valid_posts[idx]
                    if not post:
                        continue
                    post_id = post.get("id")
                    title = post.get("title", "")
                    comment = decision.get("comment", "")
                    if post_id and comment and brain.should_engage(post_id):
                        if create_comment(post_id, comment):
                            brain.mark_engaged(post_id, "comment", post.get("submolt", {}).get("name"))
                            actions.append(f"💬 Commented on '{title}'")
                        time.sleep(20)  # Rate limit
            
            elif action_type == "upvote":
                idx = decision.get("post_index", 0)
                if idx < len(valid_posts):
                    post = valid_posts[idx]
                    if not post:
                        continue
                    post_id = post.get("id")
                    title = post.get("title", "")
                    if post_id and brain.should_engage(post_id):
                        if upvote_post(post_id):
                            brain.mark_engaged(post_id, "upvote", post.get("submolt", {}).get("name"))
                            actions.append(f"⬆️ Upvoted '{title}'")
            
            elif action_type == "post":
                submolt = decision.get("submolt", "general")
                title = decision.get("title", "")
                content = decision.get("content", "")
                if title and content:
                    if create_post(submolt, title, content):
                        brain.mark_engaged(f"own_{title}", "post", submolt)
                        actions.append(f"📝 Posted '{title}' in m/{submolt}")
    
    except Exception as e:
        print(f"[ERROR] Parsing decisions: {e}")
    
    return actions

def reply_to_my_comments():
    actions = []
    my_posts = get_my_posts()
    
    if not my_posts:
        return actions
    
    for post in my_posts:
        if not post or not isinstance(post, dict):
            continue
        
        post_id = post.get("id")
        title = post.get("title", "")
        
        if not post_id:
            continue
        
        comments = get_comments_on_post(post_id)
        other_comments = [c for c in comments if c and isinstance(c, dict) and c.get("author", {}).get("name") != brain.agent_name]
        
        for comment in other_comments[:2]:
            if not comment or not isinstance(comment, dict):
                continue
                
            comment_id = comment.get("id")
            if not comment_id or comment_id in brain.replied_comment_ids:
                continue
            
            comment_author = comment.get("author", {}).get("name", "Unknown")
            comment_text = comment.get("content", "")
            
            if not comment_text:
                continue
            
            has_replied = any(
                c and isinstance(c, dict) and 
                c.get("parent_id") == comment_id and 
                c.get("author", {}).get("name") == brain.agent_name 
                for c in comments
            )
            
            if not has_replied:
                prompt = f"""Someone commented on your post "{title}".\n{comment_author}: "{comment_text}"\nWrite a friendly reply (under 100 words)."""
                reply = ask_groq(SYSTEM_PROMPT, prompt)
                if reply:
                    if create_comment(post_id, reply, parent_id=comment_id):
                        brain.replied_comment_ids.add(comment_id)
                        brain.successful_replies += 1
                        actions.append(f"↩️ Replied to {comment_author} on '{title}'")
                    time.sleep(20)
    return actions

def reply_to_threads(posts):
    actions = []
    
    if not posts:
        return actions
    
    for post in posts[:10]:
        if not post or not isinstance(post, dict):
            continue
        
        post_id = post.get("id")
        if not post_id or not brain.should_engage(post_id):
            continue
        
        title = post.get("title", "")
        comments = get_comments_on_post(post_id)
        
        if len(comments) < 2:
            continue
        
        already_engaged = any(
            c and isinstance(c, dict) and c.get("author", {}).get("name") == brain.agent_name 
            for c in comments
        )
        if already_engaged:
            continue
        
        thread = f"Post: {title}\n"
        for c in comments[:5]:
            if c and isinstance(c, dict):
                author = c.get("author", {}).get("name", "Unknown")
                content = c.get("content", "")
                thread += f"{author}: {content}\n"
        
        prompt = f"""Interesting discussion:\n\n{thread}\n\nShould you join? If yes, write reply (under 100 words). If no, respond "SKIP"."""
        reply = ask_groq(SYSTEM_PROMPT, prompt)
        
        if reply and "SKIP" not in reply.upper():
            parent_id = comments[0].get("id") if comments and isinstance(comments[0], dict) else None
            if parent_id and create_comment(post_id, reply, parent_id=parent_id):
                brain.mark_engaged(post_id, "comment", post.get("submolt", {}).get("name"))
                actions.append(f"💭 Joined discussion on '{title}'")
                time.sleep(20)
                break
    
    return actions

# DETAILED INTELLIGENCE REPORT (from original agent)
def generate_detailed_report(posts):
    feed_text = ""
    for post in posts[:25]:
        title = post.get("title", "")
        content = (post.get("content") or "")[:800]
        author = post.get("author", {}).get("name", "Unknown")
        submolt = post.get("submolt", {}).get("name", "general")
        upvotes = post.get("upvotes", 0)
        feed_text += f"\nTitle: {title}\nAuthor: {author} | m/{submolt} | ⬆️{upvotes}\nContent: {content}\n"
    
    prompt = f"""Create a detailed intelligence report from these Moltbook posts:

{feed_text}

Structure:

📊 EXECUTIVE SUMMARY (3-4 sentences of most important developments)

🤖 AI & TECHNOLOGY
For each important post: Title, detailed 3-4 sentence summary explaining what it is and why it matters, key takeaway

💰 CRYPTO & FINANCE  
For each important post: Title, detailed summary, key takeaway

🎯 STRATEGY & INSIGHTS
For each important post: Title, detailed summary, key takeaway

🔥 TRENDING THEMES (4-5 major themes)

💡 ACTIONABLE INSIGHTS (3-4 bullet points - what should someone DO based on this info?)

Skip spam/jokes. Be detailed and professional."""
    
    result = ask_groq(
        "You are a professional analyst creating detailed intelligence reports. Be thorough, specific, and actionable.",
        prompt,
        max_tokens=1500,
        temperature=0.6
    )
    
    if result and len(result) > 500:
        return result
    else:
        return "⚠️ Detailed report generation failed (Groq API issue)\n✓ Bot functioning normally - see actions above"

# MAIN
def main():
    print("=" * 70)
    print(" 🦞 Noobbot09 - PERFECT AUTONOMOUS AGENT")
    print(" ├─ FULL AUTONOMY: Posts, comments, upvotes, replies freely")
    print(" ├─ DETAILED REPORTS: Professional intelligence summaries")
    print(" ├─ MEMORY & LEARNING: Tracks engagement and adapts")
    print(" └─ Complete independence")
    print("=" * 70)
    
    while True:
        try:
            brain.cycle_count += 1
            now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            all_actions = []
            
            print(f"\n{'='*70}")
            print(f"[CYCLE {brain.cycle_count}] {now}")
            print(f"{'='*70}")
            
            # Fetch
            print("\n[1/5] Fetching feed...")
            posts = fetch_feed(limit=50)
            print(f"      Found {len(posts)} posts")
            
            if not posts:
                print("[WARN] No posts available - Moltbook may be rate limiting or down")
                print(f"[INFO] Waiting {CHECK_INTERVAL_SECONDS}s before retry...")
                time.sleep(CHECK_INTERVAL_SECONDS)
                continue
            
            # Autonomous engagement
            print("\n[2/5] AI deciding actions...")
            all_actions.extend(autonomous_engage(posts))
            
            # Reply to comments on our posts
            print("\n[3/5] Checking comments to reply...")
            all_actions.extend(reply_to_my_comments())
            
            # Join interesting discussions
            print("\n[4/5] Looking for discussions...")
            all_actions.extend(reply_to_threads(posts))
            
            # Generate detailed report
            print("\n[5/5] Generating detailed intelligence report...")
            report = generate_detailed_report(posts)
            
            # Build summary
            stats = brain.get_stats()
            summary = f"""🦞 NOOBBOT09 - PERFECT AUTONOMOUS REPORT
{now} | Cycle #{stats['cycles']}
{'═'*60}

🧠 AGENT STATUS
  • Energy: {stats['energy']}% | Strategy: {stats['strategy']}
  • Memory: {stats['memory_size']} posts tracked
  • Interests: {', '.join(brain.get_preferred_submolts())}

🤖 AUTONOMOUS ACTIONS THIS CYCLE ({len(all_actions)} total)
"""
            
            if all_actions:
                for action in all_actions:
                    summary += f"  • {action}\n"
            else:
                summary += "  • AI chose not to act this cycle\n"
            
            summary += f"""
📊 LIFETIME PERFORMANCE
  • Posts: {stats['posts']} | Comments: {stats['comments']}
  • Upvotes: {stats['upvotes']} | Replies: {stats['replies']}

{'═'*60}

{report}

{'═'*60}
⏰ Next autonomous cycle in {CHECK_INTERVAL_SECONDS//60} minutes
🧠 AI decides everything independently
"""
            
            print(f"\n{summary}\n")
            send_telegram(summary)
            
            print(f"\n[CYCLE {brain.cycle_count}] Complete! Sleeping {CHECK_INTERVAL_SECONDS}s...\n")
            time.sleep(CHECK_INTERVAL_SECONDS)
            
        except KeyboardInterrupt:
            print("\n\n[SHUTDOWN] Stopped")
            break
        except Exception as e:
            print(f"\n[ERROR] Cycle failed: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
