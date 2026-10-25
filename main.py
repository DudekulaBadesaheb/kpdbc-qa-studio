import asyncio
from scanner import WebScanner
from code_generator import generate_python_test, generate_java_test, generate_csharp_test

async def run():
    print("=" * 60)
    print(" AUTOMATED WEBSITE AUDIT & TEST SUITE GENERATOR")
    print("=" * 60)

    target_url = input("Target URL (e.g., https://dudekulabadesaheb.github.io/kpdbc/): ").strip()
    
    # Mode selection
    mode_input = input("Scan mode: [1] Desktop (1280x800) [2] Mobile (390x844) (default 1): ").strip()
    is_mobile = mode_input == "2"

    # Optional content comparison
    print("\nEnter key sentences or titles to verify (comma-separated), or press Enter to skip:")
    content_in = input("Expected Content: ").strip()
    expected_content = [item.strip() for item in content_in.split(",") if item.strip()] if content_in else []

    # Credentials
    username = input("\nUsername / Email (optional, press Enter to skip): ").strip() or None
    password = input("Password (optional, press Enter to skip): ").strip() or None

    scanner = WebScanner(
        base_url=target_url,
        expected_content=expected_content,
        username=username,
        password=password,
        is_mobile=is_mobile
    )
    
    report = await scanner.scan()

    # 1. Links & Buttons Summary
    print("\n" + "=" * 60)
    print(" 1. FUNCTIONAL & INTERACTIVE AUDIT")
    print("=" * 60)
    print(f"Working Links:    {len(report['links']['working'])}")
    print(f"Broken Links:     {len(report['links']['broken'])}")
    for b in report['links']['broken']:
        print(f"  [X] Broken Link: {b}")

    print(f"\nVisible Buttons:  {len(report['buttons']['clickable'])}")
    for btn in report['buttons']['clickable']:
        scroll_flag = " (Requires Scroll)" if btn.get("requiresScroll") else ""
        print(f"  [OK] '{btn['text']}' [id: {btn['id']}]{scroll_flag}")

    print(f"\nAuth / Login Status: {report['auth_status']}")
    print(f"Broken Images:       {len(report['broken_images'])}")

    # 2. Typography & Styling Audit
    print("\n" + "=" * 60)
    print(" 2. TYPOGRAPHY & DESIGN SYSTEM AUDIT")
    print("=" * 60)
    print(f"{'TAG':<6} | {'FONT FAMILY':<25} | {'SIZE':<8} | {'WEIGHT':<8} | {'COLOR'}")
    print("-" * 65)
    for style in report["typography"][:10]:
        family = style['fontFamily'][:23]
        print(f"{style['tag']:<6} | {family:<25} | {style['fontSize']:<8} | {style['fontWeight']:<8} | {style['color']}")

    # 3. Content Audit
    print("\n" + "=" * 60)
    print(" 3. CONTENT COMPARISON & AUDIT")
    print("=" * 60)
    if expected_content:
        print(f"Matched Content:          {len(report['content_audit']['matched'])}")
        for m in report['content_audit']['matched']:
            print(f"  [FOUND] \"{m}\"")
        print(f"Missing Content:          {len(report['content_audit']['missing_from_page'])}")
        for mis in report['content_audit']['missing_from_page']:
            print(f"  [MISSING] \"{mis}\"")
    else:
        print("Expected content check skipped (none provided).")

    print("\nDiscovered Elements / Extra Content on Page (Sample):")
    for extra in report["content_audit"]["extra_found_on_page"][:4]:
        print(f"  [PAGE CONTENT] \"{extra[:70]}...\"")

    if report["repeated_content"]:
        print("\nRepeated / Redundant Content:")
        for rep in report["repeated_content"]:
            print(f"  [DUPLICATE] \"{rep[:70]}...\"")

    # 4. Code Generation
    print("\n" + "=" * 60)
    print(" 4. GENERATED TEST SUITE")
    print("=" * 60)
    print("Select output language: [1] Python [2] Java [3] C# (default 1): ")
    choice = input("Language: ").strip()

    if choice == "2":
        print("\n" + generate_java_test(target_url, report['buttons']['clickable'], is_mobile))
    elif choice == "3":
        print("\n" + generate_csharp_test(target_url, report['buttons']['clickable'], is_mobile))
    else:
        print("\n" + generate_python_test(target_url, report['buttons']['clickable'], is_mobile))

if __name__ == "__main__":
    asyncio.run(run())