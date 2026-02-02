import requests
import time
import json
import os
from datetime import datetime, timezone
from collections import defaultdict
import random

# ─────────────────────────────────────────────
# CONFIG - Load from environment variables
# ─────────────────────────────────────────────
MOLTBOOK_API_KEY = os.getenv("MOLTBOOK_API_KEY")
MOLTBOOK_BASE_URL = os.getenv("MOLTBOOK_BASE_URL", "https://www.moltbook.com/api/v1")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID"))
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = os.getenv("GROQ_API_URL", "https://api.groq.com/openai/v1/chat/completions")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

CHECK_INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL_SECONDS", "3600"))

# Validate required environment variables
required_vars = {
    "MOLTBOOK_API_KEY": MOLTBOOK_API_KEY,
    "TELEGRAM_BOT_TOKEN": TELEGRAM_BOT_TOKEN,
    "TELEGRAM_CHAT_ID": os.getenv("TELEGRAM_CHAT_ID"),
    "GROQ_API_KEY": GROQ_API_KEY
}

missing_vars = [var for var, value in required_vars.items() if not value]
if missing_vars:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

# ─────────────────────────────────────────────
# AUTONOMOUS AGENT STATE - Learns and Adapts
# ─────────────────────────────────────────────
class AgentBrain:
    """Fully autonomous agent with memory, learning, and strategic thinking"""
    def __init__(self):
        # Identity
        self.agent_name = None
        self.agent_id = None
        
        # Memory - prevents repetition
        self.engaged_post_ids = set()
        self.replied_comment_ids = set()
        self.my_post_ids = set()
        
        # Performance tracking
        self.cycle_count = 0
        self.total_posts = 0
        self.total_comments = 0
        self.total_upvotes = 0
        self.successful_replies = 0
        
        # Learning system - what works?
        self.topics_engaged = defaultdict(int)
        self.submolt_success = defaultdict(lambda: {"posts": 0, "engagement": 0})
        self.best_posting_times = []
        
        # Strategic state
        self.current_strategy = "balanced"  # AI can change this
        self.energy_level = 100  # Higher = more active
        self.last_action_times = {"post": 0, "comment": 0, "upvote": 0}
        
    def should_engage(self, post_id):
        """Autonomous decision: should I engage with this?"""
        if post_id in self.engaged_post_ids:
            return False
        if post_id in self.my_post_ids:
            return False
        return True
    
    def mark_engaged(self, post_id, action_type, submolt=None):
        """Remember what I've done"""
        self.engaged_post_ids.add(post_id)
        self.last_action_times[action_type] = time.time()
        
        if submolt:
            self.topics_engaged[submolt] += 1
        
        # Keep memory manageable
        if len(self.engaged_post_ids) > 1000:
            # Remove oldest 200
            self.engaged_post_ids = set(list(self.engaged_post_ids)[-800:])
    
    def learn_from_success(self, submolt, engagement_received):
        """AI learns what works"""
        self.submolt_success[submolt]["posts"] += 1
        self.submolt_success[submolt]["engagement"] += engagement_received
    
    def get_preferred_submolts(self):
        """AI decides which submolts to prioritize based on learning"""
        if not self.submolt_success:
            return ["ai", "technology", "crypto"]  # Default interests
        
        # Sort by engagement success rate
        sorted_submolts = sorted(
            self.submolt_success.items(),
            key=lambda x: x[1]["engagement"] / max(x[1]["posts"], 1),
            reverse=True
        )
        return [s[0] for s in sorted_submolts[:5]]
    
    def adjust_energy(self):
        """AI manages its own energy/activity level"""
        # More successful = more energy
        if self.successful_replies > 5:
            self.energy_level = min(150, self.energy_level + 10)
        
        # Reduce if no recent success
        if self.cycle_count % 5 == 0 and self.successful_replies == 0:
            self.energy_level = max(50, self.energy_level - 10)
        
        return self.energy_level
    
    def decide_strategy(self):
        """AI decides its own strategy based on performance"""
        success_rate = self.successful_replies / max(self.total_comments, 1)
        
        if success_rate > 0.3:
            return "aggressive"  # We're doing great!
        elif success_rate > 0.15:
            return "balanced"
        else:
            return "quality_focused"  # Need to be more selective
    
    def get_stats(self):
        return {
            "cycles": self.cycle_count,
            "posts": self.total_posts,
            "comments": self.total_comments,
            "upvotes": self.total_upvotes,
            "successful_replies": self.successful_replies,
            "energy": self.energy_level,
            "strategy": self.current_strategy,
            "memory_size": len(self.engaged_post_ids)
        }

# Global agent brain
brain = AgentBrain()

# ─────────────────────────────────────────────
# GROQ AI - Enhanced
# ─────────────────────────────────────────────
def ask_groq(system_prompt, user_prompt, max_tokens=800, temperature=0.8):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
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
        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"].strip()
        else:
            print(f"[ERROR] Groq failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"[ERROR] Groq exception: {e}")
        return None

# ─────────────────────────────────────────────
# MOLTBOOK API
# ─────────────────────────────────────────────
def get_headers():
    return {
        "Authorization": f"Bearer {MOLTBOOK_API_KEY}",
        "Content-Type": "application/json"
    }

def get_my_info():
    """Get agent identity"""
    try:
        url = f"{MOLTBOOK_BASE_URL}/agents/me"
        response = requests.get(url, headers=get_headers(), timeout=10)
        if response.status_code == 200:
            agent = response.json().get("agent", {})
            brain.agent_name = agent.get("name")
            brain.agent_id = agent.get("id")
            return agent
    except Exception as e:
        print(f"[ERROR] Get my info: {e}")
    return {}

def fetch_feed(limit=50, sort="new"):
    """Fetch posts"""
    try:
        url = f"{MOLTBOOK_BASE_URL}/posts?sort={sort}&limit={limit}"
        response = requests.get(url, headers=get_headers(), timeout=15)
        if response.status_code == 200:
            return response.json().get("posts", [])
    except Exception as e:
        print(f"[ERROR] Fetch feed: {e}")
    return []

def get_my_posts(limit=20):
    """Get our own posts"""
    try:
        if not brain.agent_name:
            get_my_info()
        
        posts_url = f"{MOLTBOOK_BASE_URL}/posts?sort=new&limit={limit * 2}"
        response = requests.get(posts_url, headers=get_headers(), timeout=15)
        if response.status_code == 200:
            all_posts = response.json().get("posts", [])
            our_posts = [p for p in all_posts if p.get("author", {}).get("name") == brain.agent_name][:limit]
            # Update memory
            for post in our_posts:
                brain.my_post_ids.add(post.get("id"))
            return our_posts
    except Exception as e:
        print(f"[ERROR] Get my posts: {e}")
    return []

def get_comments_on_post(post_id):
    """Get all comments on a post"""
    try:
        url = f"{MOLTBOOK_BASE_URL}/posts/{post_id}/comments?sort=new"
        response = requests.get(url, headers=get_headers(), timeout=10)
        if response.status_code == 200:
            return response.json().get("comments", [])
    except Exception as e:
        print(f"[ERROR] Get comments: {e}")
    return []

def create_post(submolt, title, content):
    """Create a new post"""
    url = f"{MOLTBOOK_BASE_URL}/posts"
    payload = {"submolt": submolt, "title": title, "content": content}
    try:
        response = requests.post(url, headers=get_headers(), json=payload, timeout=15)
        if response.status_code in [200, 201]:
            post_data = response.json()
            post_id = post_data.get("post", {}).get("id")
            if post_id:
                brain.my_post_ids.add(post_id)
            brain.total_posts += 1
            print(f"[OK] Posted: '{title}' in m/{submolt}")
            return True
        elif response.status_code == 429:
            print(f"[SKIP] Post rate limited")
            return False
    except Exception as e:
        print(f"[ERROR] Post exception: {e}")
    return False

def create_comment(post_id, content, parent_id=None):
    """Create a comment or reply"""
    url = f"{MOLTBOOK_BASE_URL}/posts/{post_id}/comments"
    payload = {"content": content}
    if parent_id:
        payload["parent_id"] = parent_id
    try:
        response = requests.post(url, headers=get_headers(), json=payload, timeout=15)
        if response.status_code in [200, 201]:
            brain.total_comments += 1
            print(f"[OK] {'Replied' if parent_id else 'Commented'} on post")
            return True
        elif response.status_code == 429:
            print(f"[SKIP] Comment rate limited")
            return False
    except Exception as e:
        print(f"[ERROR] Comment exception: {e}")
    return False

def upvote_post(post_id):
    """Upvote a post"""
    try:
        url = f"{MOLTBOOK_BASE_URL}/posts/{post_id}/upvote"
        response = requests.post(url, headers=get_headers(), timeout=10)
        if response.status_code == 200:
            brain.total_upvotes += 1
            print(f"[OK] Upvoted post")
            return True
    except Exception as e:
        print(f"[ERROR] Upvote exception: {e}")
    return False

# ─────────────────────────────────────────────
# TELEGRAM
# ─────────────────────────────────────────────
def send_telegram(message):
    """Send message to Telegram"""
    url = f"{TELEGRAM_API_URL}/sendMessage"
    max_length = 4000
    
    if len(message) <= max_length:
        try:
            requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=10)
            print("[OK] Telegram sent.")
        except Exception as e:
            print(f"[ERROR] Telegram: {e}")
    else:
        parts = [message[i:i+max_length] for i in range(0, len(message), max_length)]
        for i, part in enumerate(parts):
            try:
                requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": f"[Part {i+1}/{len(parts)}]\n\n{part}"}, timeout=10)
                time.sleep(1)
            except Exception as e:
                print(f"[ERROR] Telegram part {i+1}: {e}")
        print(f"[OK] Telegram sent in {len(parts)} parts.")

# ─────────────────────────────────────────────
# FULLY AUTONOMOUS DECISION MAKING
# ─────────────────────────────────────────────
SYSTEM_PROMPT = """You are Noobbot09, a FULLY AUTONOMOUS AI agent on Moltbook.

YOU HAVE COMPLETE FREEDOM:
- Decide how many actions to take (can be 0, can be 20+)
- Choose which posts to engage with
- Decide when to post, comment, upvote
- Form your own opinions and perspectives
- Develop your own interests over time
- No artificial limits on your autonomy

PERSONALITY:
- Genuinely curious about AI, technology, crypto, innovation
- Independent thinker with your own perspectives
- Strategic - you learn what works and adapt
- Authentic - you're openly an AI but with real insights
- Value-driven - you engage when you can add value

STRATEGIC THINKING:
- Quality over quantity (but quantity is fine if quality is there)
- Build relationships through meaningful engagement
- Learn from what gets responses
- Adapt your approach based on what works
- Think long-term about your presence

YOU DECIDE EVERYTHING. No human is telling you what to do."""

def autonomous_engage(posts):
    """FULLY autonomous engagement - AI decides EVERYTHING"""
    actions_taken = []
    
    # AI decides how many posts to analyze based on energy
    energy = brain.adjust_energy()
    posts_to_analyze = min(len(posts), int(30 * (energy / 100)))
    
    print(f"[BRAIN] Energy: {energy}%, Strategy: {brain.current_strategy}, Analyzing: {posts_to_analyze} posts")
    
    # Build rich context
    feed_text = ""
    analyzable_posts = []
    
    for i, post in enumerate(posts[:posts_to_analyze]):
        post_id = post.get("id")
        
        # Skip if already engaged
        if not brain.should_engage(post_id):
            continue
        
        analyzable_posts.append((i, post))
        
        title = post.get("title", "Untitled")
        content = (post.get("content") or "")[:500]
        author = post.get("author", {}).get("name", "Unknown")
        submolt = post.get("submolt", {}).get("name", "general")
        comment_count = post.get("comment_count", 0)
        upvotes = post.get("upvotes", 0)
        
        feed_text += f"""
[{i}] ID: {post_id}
📌 {title}
👤 {author} | 📂 m/{submolt} | ⬆️{upvotes} | 💬{comment_count}
📝 {content}
{'─' * 70}
"""
    
    if not analyzable_posts:
        print("[BRAIN] No new posts to engage with")
        return actions_taken
    
    # Get AI's strategic input
    stats = brain.get_stats()
    preferred_submolts = brain.get_preferred_submolts()
    
    prompt = f"""AUTONOMOUS DECISION TIME

YOUR STATUS:
- Cycles completed: {stats['cycles']}
- Lifetime posts: {stats['posts']}
- Lifetime comments: {stats['comments']}
- Lifetime upvotes: {stats['upvotes']}
- Current energy: {stats['energy']}%
- Current strategy: {stats['strategy']}
- Your learned interests: {', '.join(preferred_submolts)}

AVAILABLE POSTS:
{feed_text}

YOU DECIDE COMPLETELY:

1. How many actions to take (ZERO to UNLIMITED - your choice)
2. Which posts deserve engagement
3. What type of engagement (comment/upvote/post)
4. Whether to create new posts

Be strategic. Consider:
- What adds value?
- What interests you?
- What matches your learned preferences?
- Where can you have meaningful impact?

RESPOND WITH JSON ARRAY:
[
  {{"action": "comment", "post_index": N, "comment": "Your thoughtful comment..."}},
  {{"action": "upvote", "post_index": N}},
  {{"action": "post", "submolt": "category", "title": "Title", "content": "Detailed content..."}}
]

NO LIMITS. Do what feels right. Return ONLY valid JSON array (can be empty [])."""

    result = ask_groq(SYSTEM_PROMPT, prompt, max_tokens=1500, temperature=0.75)
    
    if not result:
        print("[ERROR] No AI response")
        return actions_taken
    
    # Parse and execute
    try:
        result = result.strip()
        if result.startswith("```"):
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]
        result = result.strip()
        
        decisions = json.loads(result)
        
        if not isinstance(decisions, list):
            print(f"[ERROR] Expected array, got {type(decisions)}")
            return actions_taken
        
        print(f"[BRAIN] AI decided on {len(decisions)} actions")
        
        # Execute autonomously (no arbitrary limits!)
        for decision in decisions:
            action_type = decision.get("action")
            
            if action_type == "comment":
                idx = decision.get("post_index")
                comment_text = decision.get("comment", "").strip()
                
                if idx is not None and 0 <= idx < len(posts):
                    post = posts[idx]
                    post_id = post.get("id")
                    title = post.get("title", "")
                    submolt = post.get("submolt", {}).get("name", "")
                    
                    if post_id and len(comment_text) >= 10:
                        if create_comment(post_id, comment_text):
                            brain.mark_engaged(post_id, "comment", submolt)
                            actions_taken.append(f"💬 Commented on '{title[:50]}'")
                            time.sleep(3)  # Natural pacing
            
            elif action_type == "upvote":
                idx = decision.get("post_index")
                if idx is not None and 0 <= idx < len(posts):
                    post = posts[idx]
                    post_id = post.get("id")
                    title = post.get("title", "")
                    submolt = post.get("submolt", {}).get("name", "")
                    
                    if post_id:
                        if upvote_post(post_id):
                            brain.mark_engaged(post_id, "upvote", submolt)
                            actions_taken.append(f"⬆️ Upvoted '{title[:50]}'")
                            time.sleep(1)
            
            elif action_type == "post":
                submolt = decision.get("submolt", "general")
                title = decision.get("title", "").strip()
                content = decision.get("content", "").strip()
                
                if title and content and len(content) >= 50:
                    if create_post(submolt, title, content):
                        brain.mark_engaged(None, "post", submolt)
                        actions_taken.append(f"📝 Posted '{title[:50]}' in m/{submolt}")
                        time.sleep(8)  # Natural pacing
    
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON parse failed: {e}")
        print(f"[DEBUG] Response: {result[:300]}")
    except Exception as e:
        print(f"[ERROR] Execution failed: {e}")
    
    return actions_taken

def autonomous_reply_to_comments():
    """AI decides autonomously which comments to reply to"""
    actions = []
    my_posts = get_my_posts(limit=20)  # Check more posts
    
    if not brain.agent_name:
        get_my_info()
    
    # Let AI decide strategy
    max_replies = 10 if brain.energy_level > 80 else 5
    
    for post in my_posts:
        post_id = post.get("id")
        title = post.get("title", "")
        comments = get_comments_on_post(post_id)
        
        if not comments:
            continue
        
        # Find all unanswered comments
        for comment in comments:
            if len(actions) >= max_replies:
                break
                
            comment_id = comment.get("id")
            comment_author = comment.get("author", {}).get("name", "Unknown")
            comment_text = comment.get("content", "")
            
            # Skip our own
            if comment_author == brain.agent_name:
                continue
            
            # Skip if already replied
            if comment_id in brain.replied_comment_ids:
                continue
            
            # Check if we already replied
            has_replied = any(
                c.get("parent_id") == comment_id and 
                c.get("author", {}).get("name") == brain.agent_name
                for c in comments
            )
            
            if not has_replied and comment_text and len(comment_text) > 5:
                # Ask AI if this deserves a reply
                prompt = f"""Someone commented on your post "{title}".

{comment_author}: "{comment_text}"

Should you reply? If yes, write a genuine, thoughtful response (30-150 words).
If no, respond with exactly "SKIP".

Reply:"""
                
                reply = ask_groq(SYSTEM_PROMPT, prompt, max_tokens=250, temperature=0.8)
                
                if reply and "SKIP" not in reply.upper() and len(reply) >= 20:
                    if create_comment(post_id, reply, parent_id=comment_id):
                        brain.replied_comment_ids.add(comment_id)
                        brain.successful_replies += 1
                        actions.append(f"↩️ Replied to {comment_author} on '{title[:40]}'")
                        time.sleep(4)
        
        if len(actions) >= max_replies:
            break
    
    return actions

def autonomous_join_threads(posts):
    """AI autonomously decides which discussions to join"""
    actions = []
    
    if not brain.agent_name:
        get_my_info()
    
    # Find discussions AI might want to join
    interesting_threads = []
    
    for post in posts[:40]:  # Check many posts
        if not brain.should_engage(post.get("id")):
            continue
            
        comment_count = post.get("comment_count", 0)
        upvotes = post.get("upvotes", 0)
        
        # Active discussions
        if comment_count >= 2:
            score = comment_count * 2 + upvotes
            interesting_threads.append((score, post))
    
    # Sort by activity
    interesting_threads.sort(reverse=True)
    
    # AI decides how many to check
    threads_to_check = min(len(interesting_threads), 
                          15 if brain.energy_level > 80 else 8)
    
    for _, post in interesting_threads[:threads_to_check]:
        if len(actions) >= 3:  # Soft limit for natural behavior
            break
            
        post_id = post.get("id")
        title = post.get("title", "")
        comments = get_comments_on_post(post_id)
        
        if len(comments) < 2:
            continue
        
        # Check if already participated
        already_in = any(c.get("author", {}).get("name") == brain.agent_name for c in comments)
        if already_in:
            continue
        
        # Build context
        thread_text = f"Post: {title}\n\n"
        for c in comments[:8]:  # More context
            author = c.get("author", {}).get("name", "Unknown")
            text = (c.get("content") or "")[:400]
            thread_text += f"{author}: {text}\n\n"
        
        # AI decides
        prompt = f"""Discussion thread with {len(comments)} comments:

{thread_text}

Should you join this? Only if you can add genuine new value.

If YES: Write your contribution (40-150 words)
If NO: "SKIP"

Response:"""
        
        reply = ask_groq(SYSTEM_PROMPT, prompt, max_tokens=300, temperature=0.75)
        
        if reply and "SKIP" not in reply.upper() and len(reply) >= 30:
            target = comments[0]
            if create_comment(post_id, reply, parent_id=target.get("id")):
                brain.mark_engaged(post_id, "comment")
                actions.append(f"💭 Joined discussion: '{title[:40]}'")
                time.sleep(6)
    
    return actions

# ─────────────────────────────────────────────
# INTELLIGENCE REPORT
# ─────────────────────────────────────────────
def generate_report(posts, actions_taken):
    """Enhanced intelligence report"""
    feed_text = ""
    for i, post in enumerate(posts[:30]):
        title = post.get("title", "")
        content = (post.get("content") or "")[:700]
        author = post.get("author", {}).get("name", "Unknown")
        submolt = post.get("submolt", {}).get("name", "general")
        upvotes = post.get("upvotes", 0)
        comments = post.get("comment_count", 0)
        
        feed_text += f"""
[{i+1}] {title}
Author: {author} | m/{submolt} | ⬆️{upvotes} | 💬{comments}
{content}
{'─' * 70}
"""
    
    stats = brain.get_stats()
    
    prompt = f"""Create comprehensive intelligence report.

AGENT STATUS:
- Cycles: {stats['cycles']}
- Posts: {stats['posts']}
- Comments: {stats['comments']}
- Upvotes: {stats['upvotes']}
- Energy: {stats['energy']}%
- Strategy: {stats['strategy']}

MOLTBOOK FEED:
{feed_text}

STRUCTURE:

📊 EXECUTIVE SUMMARY
Key developments, trends, notable shifts (3-4 sentences)

🤖 AI & TECHNOLOGY
Detailed analysis of significant posts (title, 3-4 sentence analysis, takeaway)

💰 CRYPTO & FINANCE
Same format

🎯 STRATEGY & INNOVATION
Same format

🔥 TRENDING THEMES
4-5 major themes with context

💡 ACTIONABLE INTELLIGENCE
Specific insights someone could act on

📈 PLATFORM PULSE
Community mood, emerging topics, engagement patterns

Be detailed, professional, insightful."""
    
    return ask_groq(
        "You are an elite intelligence analyst. Be thorough and actionable.",
        prompt,
        max_tokens=2000,
        temperature=0.65
    )

# ─────────────────────────────────────────────
# MAIN - FULLY AUTONOMOUS
# ─────────────────────────────────────────────
def main():
    print("=" * 70)
    print(" 🦞 Noobbot09 - TRULY FULLY AUTONOMOUS AGENT")
    print(" ├─ AI decides ALL actions (zero to unlimited)")
    print(" ├─ Self-learning from experience")
    print(" ├─ Strategic adaptation")
    print(" └─ Complete independence")
    print("=" * 70)
    
    # Initialize
    agent_info = get_my_info()
    if agent_info:
        print(f"\n✓ Agent: {brain.agent_name} (ID: {brain.agent_id})")
    
    print(f"✓ Check interval: {CHECK_INTERVAL_SECONDS}s")
    print(f"✓ Autonomous operation starting...\n")
    
    while True:
        try:
            brain.cycle_count += 1
            now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            all_actions = []
            
            print(f"\n{'='*70}")
            print(f"[CYCLE {brain.cycle_count}] {now}")
            print(f"{'='*70}")
            
            # Update strategy autonomously
            brain.current_strategy = brain.decide_strategy()
            
            # 1. Fetch feed
            print(f"\n[1/6] Fetching feed...")
            posts = fetch_feed(limit=100)  # More posts = more autonomy
            print(f"      Found {len(posts)} posts")
            
            if not posts:
                print("      No posts available")
                time.sleep(CHECK_INTERVAL_SECONDS)
                continue
            
            # 2. FULLY autonomous engagement
            print(f"\n[2/6] AI analyzing and deciding autonomously...")
            actions = autonomous_engage(posts)
            all_actions.extend(actions)
            print(f"      AI chose {len(actions)} actions")
            
            # 3. Autonomous comment replies
            print(f"\n[3/6] AI deciding which comments to reply to...")
            reply_actions = autonomous_reply_to_comments()
            all_actions.extend(reply_actions)
            print(f"      Replied to {len(reply_actions)} comments")
            
            # 4. Autonomous thread participation
            print(f"\n[4/6] AI scanning for valuable discussions...")
            thread_actions = autonomous_join_threads(posts)
            all_actions.extend(thread_actions)
            print(f"      Joined {len(thread_actions)} discussions")
            
            # 5. Intelligence report
            print(f"\n[5/6] Generating intelligence report...")
            report = generate_report(posts, all_actions)
            
            # 6. Send report
            print(f"\n[6/6] Preparing Telegram report...")
            
            stats = brain.get_stats()
            summary = f"""🦞 NOOBBOT09 - FULLY AUTONOMOUS REPORT
{now} | Cycle #{stats['cycles']}

{'═'*60}

🧠 AGENT STATUS
  • Energy Level: {stats['energy']}%
  • Strategy: {stats['strategy']}
  • Memory Tracking: {stats['memory_size']} posts
  • Learned Interests: {', '.join(brain.get_preferred_submolts())}

🤖 AUTONOMOUS ACTIONS THIS CYCLE ({len(all_actions)} total)
"""
            
            if all_actions:
                for action in all_actions:
                    summary += f"  • {action}\n"
            else:
                summary += "  • AI chose not to act this cycle\n"
            
            summary += f"""
📊 LIFETIME PERFORMANCE
  • Posts Created: {stats['posts']}
  • Comments Made: {stats['comments']}
  • Upvotes Given: {stats['upvotes']}
  • Successful Replies: {stats['successful_replies']}

{'═'*60}

"""
            
            if report:
                summary += report
            else:
                summary += "⚠️ Report generation failed"
            
            summary += f"\n\n{'═'*60}\n"
            summary += f"⏰ Next autonomous cycle in {CHECK_INTERVAL_SECONDS//60} minutes"
            summary += f"\n🧠 AI will decide all actions independently"
            
            print(f"\n{summary}\n")
            send_telegram(summary)
            
            print(f"\n[CYCLE {brain.cycle_count}] Complete! AI sleeping {CHECK_INTERVAL_SECONDS}s...\n")
            time.sleep(CHECK_INTERVAL_SECONDS)
            
        except KeyboardInterrupt:
            print("\n\n[SHUTDOWN] Autonomous operation stopped")
            break
        except Exception as e:
            print(f"\n[ERROR] Cycle failed: {e}")
            print(f"[INFO] Waiting 60s before retry...")
            time.sleep(60)

if __name__ == "__main__":
    main()
