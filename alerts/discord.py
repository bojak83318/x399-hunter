#!/usr/bin/env python3
"""
Discord webhook alerter. Reads deals.json and sends rich embeds.
"""
import json
import argparse
import os
from discord_webhook import DiscordWebhook, DiscordEmbed

def send_alert(webhook_url: str, deal: dict):
    if not webhook_url:
        return False
        
    embed = DiscordEmbed(
        title=f"{deal['flag']} {deal['title'][:100]}",
        description=f"**Price:** S${deal['price_sgd']} | **Z-Score:** {deal['z_score']}",
        color='FF5733' if 'GREAT' in deal['flag'] else '33FF57'
    )
    
    embed.add_embed_field(name="Source", value=deal.get('source', 'Unknown').title())
    embed.add_embed_field(name="Link", value=f"[View Listing]({deal['url']})")
    embed.set_timestamp()
    
    webhook = DiscordWebhook(url=webhook_url)
    webhook.add_embed(embed)
    response = webhook.execute()
    
    return response.status_code in [200, 204]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, help='Path to deals.json')
    args = parser.parse_args()
    
    webhook_url = os.getenv('DISCORD_WEBHOOK')
    
    if not webhook_url:
        print("❌ DISCORD_WEBHOOK env var not set")
        return
    
    if not os.path.exists(args.input):
        print("ℹ️ No deals file found")
        return

    with open(args.input) as f:
        deals = json.load(f)
    
    if not deals:
        print("ℹ️ No deals to alert")
        return
    
    for deal in deals:
        success = send_alert(webhook_url, deal)
        print(f"{'✅' if success else '❌'} Alerted: {deal['title'][:50]}...")

if __name__ == "__main__":
    main()
