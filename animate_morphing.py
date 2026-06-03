# animate_morphing.py
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.patches import Patch
import os

def main():
    print("[*] Generating traffic morphing visualization frames...")
    
    # Setup styling
    plt.style.use('dark_background')
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    fig.suptitle("🛡️ DoH-Shield: Traffic Morphing vs. Website Fingerprinting Attacks", fontsize=16, fontweight='bold', color='#4fc3f7')
    
    # Data definitions
    # Original traffic: 5 packets (size in bytes, relative times in seconds)
    orig_times = np.array([0.1, 0.25, 0.4, 0.6, 0.85])
    orig_sizes = np.array([72, 120, 85, 110, 68])
    
    # Morphed traffic: original shifted in size, Laplace noise added to timing, plus 6 dummies
    # Centroid mode target size is 180 bytes
    centroid_size = 180
    alpha = 0.35
    morphed_sizes = (1 - alpha) * orig_sizes + alpha * centroid_size # [109.8, 141.0, 118.25, 134.5, 107.2]
    
    # Add timing noise
    morphed_orig_times = orig_times + np.array([0.02, 0.05, 0.09, 0.12, 0.18])
    
    # Dummy packets (to be injected asynchronously)
    dummy_times = np.array([0.18, 0.35, 0.52, 0.7, 0.8, 0.95])
    dummy_sizes = np.full(len(dummy_times), centroid_size)
    
    # Combine morphed original and dummy packets for timeline sorting
    all_morphed_times = np.concatenate([morphed_orig_times, dummy_times])
    all_morphed_sizes = np.concatenate([morphed_sizes, dummy_sizes])
    all_morphed_types = np.concatenate([np.zeros(len(orig_times)), np.ones(len(dummy_times))]) # 0=orig, 1=dummy
    
    # Sort by time
    sort_idx = np.argsort(all_morphed_times)
    all_morphed_times = all_morphed_times[sort_idx]
    all_morphed_sizes = all_morphed_sizes[sort_idx]
    all_morphed_types = all_morphed_types[sort_idx]
    
    # Set limits and styling
    for ax in (ax1, ax2):
        ax.set_xlim(-0.05, 1.2)
        ax.set_ylim(0, 230)
        ax.set_xlabel("Time (Seconds)", fontsize=11, color='#b0bec5')
        ax.set_ylabel("Packet Size (Bytes)", fontsize=11, color='#b0bec5')
        ax.grid(color='#37474f', linestyle='--', alpha=0.5)
        
    ax1.set_title("❌ Undefended DoH Flow\n(Metadata leaks website identity)", fontsize=13, color='#e57373', fontweight='bold')
    ax2.set_title("🛡️ Morphed DoH-Shield Flow\n(Indistinguishable cluster + DP timing)", fontsize=13, color='#81c784', fontweight='bold')
    
    # Info texts placeholders
    info1 = ax1.text(0.05, 210, "", color='#ff8a80', fontsize=11, fontweight='bold')
    info2 = ax2.text(0.05, 210, "", color='#a5d6a7', fontsize=11, fontweight='bold')
    
    # Classifier prediction bar plots placeholders (at the bottom)
    # We will show classification confidence bars
    c_labels = ['google.com', 'youtube.com', 'facebook.com', 'other']
    
    # We add inset axes for the classifier confidence display
    inset1 = ax1.inset_axes([0.65, 0.6, 0.32, 0.35])
    inset2 = ax2.inset_axes([0.65, 0.6, 0.32, 0.35])
    
    for inset in (inset1, inset2):
        inset.set_facecolor('#1a1a1a')
        inset.spines['top'].set_visible(False)
        inset.spines['right'].set_visible(False)
        inset.spines['left'].set_color('#78909c')
        inset.spines['bottom'].set_color('#78909c')
        inset.tick_params(colors='#cfd8dc', labelsize=8)
        inset.set_title("Attacker Confidence", fontsize=9, color='#cfd8dc')
        inset.set_xlim(0, 1.0)
        
    inset1.set_yticks(range(len(c_labels)))
    inset1.set_yticklabels(c_labels)
    inset2.set_yticks(range(len(c_labels)))
    inset2.set_yticklabels(c_labels)
    
    # Animation update function
    # 40 frames total
    total_frames = 40
    
    def update(frame):
        ax1.containers = []
        ax2.containers = []
        inset1.clear()
        inset2.clear()
        
        # Reset instet configs after clear
        for inset in (inset1, inset2):
            inset.set_facecolor('#1a1a1a')
            inset.set_xlim(0, 1.0)
            inset.tick_params(colors='#cfd8dc', labelsize=8)
            
        inset1.set_yticks(range(len(c_labels)))
        inset1.set_yticklabels(c_labels)
        inset1.set_title("CNN Attacker Confidence", fontsize=8, color='#cfd8dc')
        
        inset2.set_yticks(range(len(c_labels)))
        inset2.set_yticklabels(c_labels)
        inset2.set_title("CNN Attacker Confidence", fontsize=8, color='#cfd8dc')
        
        # Time threshold for current frame
        t_limit = (frame / total_frames) * 1.1
        
        # 1. Plot Undefended
        active_orig_idx = orig_times <= t_limit
        if np.any(active_orig_idx):
            times_to_plot = orig_times[active_orig_idx]
            sizes_to_plot = orig_sizes[active_orig_idx]
            # Plot as bar impulses
            ax1.bar(times_to_plot, sizes_to_plot, width=0.015, color='#e53935', edgecolor='white', alpha=0.9, align='center')
            
        # 2. Plot Morphed
        active_morph_idx = all_morphed_times <= t_limit
        if np.any(active_morph_idx):
            m_times = all_morphed_times[active_morph_idx]
            m_sizes = all_morphed_sizes[active_morph_idx]
            m_types = all_morphed_types[active_morph_idx]
            
            # Draw original morphed (blue-green) and dummies (orange)
            orig_mask = m_types == 0
            dummy_mask = m_types == 1
            
            if np.any(orig_mask):
                ax2.bar(m_times[orig_mask], m_sizes[orig_mask], width=0.015, color='#0288d1', edgecolor='white', alpha=0.9, align='center')
            if np.any(dummy_mask):
                ax2.bar(m_times[dummy_mask], m_sizes[dummy_mask], width=0.015, color='#f57c00', edgecolor='white', alpha=0.9, align='center')
                
        # 3. Update Text Info and Insets
        if t_limit < 0.3:
            info1.set_text("Flow Status: Session Start")
            info2.set_text("Flow Status: Session Start")
            # Initial random-looking confidence
            conf1 = [0.25, 0.25, 0.25, 0.25]
            conf2 = [0.25, 0.25, 0.25, 0.25]
        elif t_limit < 0.9:
            info1.set_text("Flow Status: DNS Burst Active")
            info2.set_text("Flow Status: Dummies Injected")
            # Undefended begins accumulating leak
            conf1 = [0.75, 0.10, 0.05, 0.10]
            conf2 = [0.28, 0.24, 0.26, 0.22]
        else:
            info1.set_text("Flow Status: Finished\nResult: ❌ Leaked website identity!")
            info2.set_text("Flow Status: Inactivity Morphed\nResult: 🛡️ Privacy Bound Holds (37.08%)")
            # Final state
            conf1 = [0.99, 0.00, 0.00, 0.01]
            conf2 = [0.27, 0.25, 0.23, 0.25]
            
        # Draw confidence bars
        inset1.barh(range(len(c_labels)), conf1, color=['#e53935', '#78909c', '#78909c', '#78909c'], alpha=0.8, height=0.6)
        inset2.barh(range(len(c_labels)), conf2, color='#4caf50', alpha=0.8, height=0.6)
        
        # Legend configuration
        legend_elements_1 = [Patch(facecolor='#e53935', label='Original DoH Packet')]
        legend_elements_2 = [Patch(facecolor='#0288d1', label='Morphed Packet (Size shifted)'),
                             Patch(facecolor='#f57c00', label='Asynchronous Padded Dummy')]
        
        ax1.legend(handles=legend_elements_1, loc='upper left', fontsize=9)
        ax2.legend(handles=legend_elements_2, loc='upper left', fontsize=9)
        
        # Fix layouts
        plt.tight_layout()
        
    print("[*] Building animated GIF...")
    ani = animation.FuncAnimation(fig, update, frames=total_frames, interval=150)
    ani.save('doh_shield_morphing.gif', writer='pillow', fps=7)
    plt.close()
    
    print("[+] Successfully generated: doh_shield_morphing.gif")
    print(f"    - Dimensions: 1500x600 px")
    print(f"    - File Size: {os.path.getsize('doh_shield_morphing.gif') / 1024:.1f} KB")

if __name__ == '__main__':
    main()
