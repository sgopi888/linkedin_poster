import subprocess
import sys

USER_INPUT = " ".join(sys.argv[1:])

print(f"\nINPUT:\n{USER_INPUT}")

# =========================================
# STEP 1 — GENERATE CONTENT
# =========================================

subprocess.run([
    "python",
    "scripts/content_orchestrator.py",
    USER_INPUT
])

# =========================================
# STEP 2 — GENERATE IMAGE
# =========================================

subprocess.run([
    "python",
    "scripts/image_agent.py"
])

# =========================================
# STEP 3 — APPROVAL
# =========================================

approval = input("\nPost to LinkedIn? (yes/no): ")

if approval.lower() == "yes":

    subprocess.run([
        "python",
        "scripts/post_to_linkedin.py"
    ])

else:
    print("\nPosting cancelled.")