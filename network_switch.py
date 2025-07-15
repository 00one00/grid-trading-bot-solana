#!/usr/bin/env python3
"""
Network Switch Utility
======================

Easy utility to switch between devnet and mainnet configurations.
Updates the .env file with appropriate network settings.
"""

import os
import sys
from dotenv import load_dotenv, set_key, find_dotenv

def load_current_config():
    """Load current configuration from .env file."""
    load_dotenv()
    
    current_network = os.getenv('NETWORK', 'devnet')
    current_capital = os.getenv('CAPITAL')
    current_rpc = os.getenv('RPC_URL')
    
    return {
        'network': current_network,
        'capital': current_capital,
        'rpc_url': current_rpc
    }

def switch_to_devnet():
    """Switch configuration to devnet."""
    print("🔄 SWITCHING TO DEVNET")
    print("="*40)
    
    env_file = find_dotenv()
    if not env_file:
        print("❌ No .env file found. Create one from env.example first.")
        return False
    
    try:
        # Update network setting
        set_key(env_file, 'NETWORK', 'devnet')
        
        # Remove any custom RPC override to use network-based selection
        set_key(env_file, 'RPC_URL', '')
        
        # Remove custom capital override to use network-based selection
        set_key(env_file, 'CAPITAL', '')
        
        print("✅ Network set to: devnet")
        print("✅ RPC URL: Auto-selected (https://api.devnet.solana.com)")
        print("✅ Capital: Auto-selected (0.1 SOL)")
        print()
        print("🔧 Configuration updated in .env file")
        print("💡 Devnet SOL is free - get it from: https://faucet.solana.com/")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to update .env file: {e}")
        return False

def switch_to_mainnet():
    """Switch configuration to mainnet with safety prompts."""
    print("🚨 SWITCHING TO MAINNET")
    print("="*40)
    print("⚠️  WARNING: Mainnet uses real money!")
    print()
    
    # Safety confirmation
    confirm = input("Are you sure you want to switch to mainnet? (y/N): ")
    if confirm.lower() != 'y':
        print("⏸️  Switch to mainnet cancelled")
        return False
    
    # Capital configuration
    print("\n💰 CAPITAL CONFIGURATION")
    print("Recommended starting amounts:")
    print("  • First time: $50-$100")
    print("  • After testing: $200-$500")
    print("  • Experienced: $500+")
    print()
    
    capital_input = input("Enter capital amount in USD (or press Enter for default $250): ")
    if capital_input.strip():
        try:
            capital = float(capital_input)
            if capital < 50:
                print("⚠️  WARNING: Very low capital amount")
            elif capital > 1000:
                print("⚠️  WARNING: High capital amount for testing")
                confirm_high = input("Proceed with high amount? (y/N): ")
                if confirm_high.lower() != 'y':
                    print("⏸️  Switch cancelled")
                    return False
        except ValueError:
            print("❌ Invalid capital amount")
            return False
    else:
        capital = None  # Use default
    
    env_file = find_dotenv()
    if not env_file:
        print("❌ No .env file found. Create one from env.example first.")
        return False
    
    try:
        # Update network setting
        set_key(env_file, 'NETWORK', 'mainnet')
        
        # Remove any custom RPC override to use network-based selection
        set_key(env_file, 'RPC_URL', '')
        
        # Set capital if specified
        if capital:
            set_key(env_file, 'CAPITAL', str(capital))
        else:
            set_key(env_file, 'CAPITAL', '')  # Use default
        
        print("✅ Network set to: mainnet")
        print("✅ RPC URL: Auto-selected (https://api.mainnet-beta.solana.com)")
        print(f"✅ Capital: {f'${capital}' if capital else 'Default ($250)'}")
        print()
        print("🔧 Configuration updated in .env file")
        print("⚠️  Remember: Start with small amounts for testing!")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to update .env file: {e}")
        return False

def show_current_config():
    """Display current network configuration."""
    config = load_current_config()
    
    print("📋 CURRENT CONFIGURATION")
    print("="*40)
    print(f"Network: {config['network']}")
    
    if config['rpc_url']:
        print(f"RPC URL: {config['rpc_url']} (custom)")
    else:
        if config['network'] == 'devnet':
            print("RPC URL: https://api.devnet.solana.com (auto)")
        else:
            print("RPC URL: https://api.mainnet-beta.solana.com (auto)")
    
    if config['capital']:
        print(f"Capital: ${config['capital']} (custom)")
    else:
        if config['network'] == 'devnet':
            print("Capital: 0.1 SOL (auto)")
        else:
            print("Capital: $250 (auto)")
    
    print()

def test_configuration():
    """Test current configuration by loading it."""
    print("🧪 TESTING CURRENT CONFIGURATION")
    print("="*40)
    
    try:
        from config import Config
        config = Config()
        
        print(f"✅ Network: {config.NETWORK}")
        print(f"✅ RPC URL: {config.RPC_URL}")
        print(f"✅ Capital: {config.CAPITAL}")
        print(f"✅ Is Devnet: {config.is_devnet}")
        print(f"✅ Explorer: {config.explorer_url}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def main():
    """Main network switch utility."""
    print("🔄 SOLANA GRID BOT - NETWORK SWITCH UTILITY")
    print("="*60)
    print("This utility helps you switch between devnet and mainnet")
    print("="*60)
    print()
    
    while True:
        show_current_config()
        
        print("OPTIONS:")
        print("1. Switch to devnet (safe testing)")
        print("2. Switch to mainnet (real trading)")
        print("3. Test current configuration") 
        print("4. Exit")
        print()
        
        choice = input("Select option (1-4): ").strip()
        
        if choice == '1':
            print()
            if switch_to_devnet():
                print("🎉 Successfully switched to devnet!")
                print("💡 Run: python3 test_devnet.py")
            else:
                print("❌ Failed to switch to devnet")
            print()
            
        elif choice == '2':
            print()
            if switch_to_mainnet():
                print("🎉 Successfully switched to mainnet!")
                print("⚠️  Run: python3 test_mainnet.py")
            else:
                print("❌ Failed to switch to mainnet")
            print()
            
        elif choice == '3':
            print()
            if test_configuration():
                print("🎉 Configuration is valid!")
            else:
                print("❌ Configuration has issues")
            print()
            
        elif choice == '4':
            print("👋 Goodbye!")
            break
            
        else:
            print("❌ Invalid option. Please select 1-4.")
            print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏸️  Network switch utility interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)