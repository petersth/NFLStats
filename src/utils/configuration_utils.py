# src/utils/configuration_utils.py - Configuration utility functions

from typing import Dict, List
import pandas as pd
import logging

logger = logging.getLogger(__name__)

# Static configuration data
CONFIGURATIONS = {
    'nfl_official': {
        'name': 'NFL Official',
        'description': 'Includes QB kneels and spikes (official NFL methodology)',
        'include_qb_kneels_rushing': True,
        'include_qb_kneels_success_rate': True,
        'include_spikes_completion': True,
        'include_spikes_success_rate': True
    },
    'analytics_clean': {
        'name': 'Analytics (Clean)',
        'description': 'Excludes QB kneels and spikes for pure efficiency metrics',
        'include_qb_kneels_rushing': False,
        'include_qb_kneels_success_rate': False,
        'include_spikes_completion': False,
        'include_spikes_success_rate': False
    },
    'custom': {
        'name': 'Custom',
        'description': 'User-defined QB kneel and spike settings',
        'include_qb_kneels_rushing': True,
        'include_qb_kneels_success_rate': True,
        'include_spikes_completion': True,
        'include_spikes_success_rate': True
    }
}


def get_configuration(config_name: str) -> Dict:
    """Get configuration by name."""
    if config_name not in CONFIGURATIONS:
        raise ValueError(f"Unknown configuration: {config_name}")
    return CONFIGURATIONS[config_name].copy()


def get_available_configurations() -> List[str]:
    """Get list of available configuration names."""
    return list(CONFIGURATIONS.keys())


def apply_configuration_to_data(data: pd.DataFrame, config: Dict) -> pd.DataFrame:
    """Apply configuration filtering to NFL play-by-play data.
    
    Configuration Filtering Strategy:
    1. QB Kneels: Can be excluded from rushing stats, success rate, or both
    2. QB Spikes: Can be excluded from completion %, success rate, or both  
    3. Context Marking: Uses special columns (_qb_kneel_context, _spike_context)
       to enable metric-specific exclusions in downstream calculations
    
    This approach allows fine-grained control where certain plays can be excluded
    from some metrics but included in others, matching real NFL analytics practices.
    
    Args:
        data: DataFrame containing NFL play-by-play data
        config: Configuration dictionary with filtering settings
        
    Returns:
        DataFrame with configuration-based filtering applied and context markers added
    """
    if len(data) == 0:
        return data
    
    # Safety check for None config
    if config is None:
        logger.warning("Configuration is None, using default settings")
        config = {}
    
    filtered_data = data.copy()
    
    # Apply QB kneel filtering based on configuration
    # QB kneels are typically used to run out the clock and may skew rushing statistics
    if 'play_type' in filtered_data.columns:
        qb_kneel_mask = filtered_data['play_type'] == 'qb_kneel'
        qb_kneels_exist = qb_kneel_mask.any()
        
        if qb_kneels_exist:
            include_rushing = config.get('include_qb_kneels_rushing', True)
            include_success_rate = config.get('include_qb_kneels_success_rate', True)
            
            # Apply filtering logic based on configuration matrix
            if not include_rushing and not include_success_rate:
                # Complete exclusion: remove QB kneels entirely
                filtered_data = filtered_data[~qb_kneel_mask]
                logger.info(f"Removed {qb_kneel_mask.sum()} QB kneel plays from analysis")
            elif not include_rushing and include_success_rate:
                # Partial exclusion: mark for context-aware filtering
                # QB kneels excluded from rushing metrics but included in success rate
                filtered_data.loc[qb_kneel_mask, '_qb_kneel_context'] = 'exclude_rushing'
                logger.info(f"Marked {qb_kneel_mask.sum()} QB kneel plays to exclude from rushing metrics only")
            elif include_rushing and not include_success_rate:
                # Filter QB kneels from success rate but keep for rushing
                filtered_data.loc[qb_kneel_mask, '_qb_kneel_context'] = 'exclude_success_rate'
                logger.info(f"Marked {qb_kneel_mask.sum()} QB kneel plays to exclude from success rate only")
            # If both are True, keep all QB kneels (no filtering needed)
    
    # Apply QB spike filtering based on configuration
    if 'play_type' in filtered_data.columns:
        qb_spike_mask = filtered_data['play_type'] == 'qb_spike'
        qb_spikes_exist = qb_spike_mask.any()
        
        if qb_spikes_exist:
            include_spikes_completion = config.get('include_spikes_completion', True)
            include_spikes_success_rate = config.get('include_spikes_success_rate', True)
            
            # Apply filtering logic for spikes
            if not include_spikes_completion and not include_spikes_success_rate:
                # Exclude from both completion % and success rate
                filtered_data.loc[qb_spike_mask, '_spike_context'] = 'exclude_both'
                logger.info(f"Marked {qb_spike_mask.sum()} QB spike plays to exclude from both completion % and success rate")
            elif not include_spikes_completion and include_spikes_success_rate:
                # Exclude from completion % only
                filtered_data.loc[qb_spike_mask, '_spike_context'] = 'exclude_completion'
                logger.info(f"Marked {qb_spike_mask.sum()} QB spike plays to exclude from completion percentage only")
            elif include_spikes_completion and not include_spikes_success_rate:
                # Exclude from success rate only
                filtered_data.loc[qb_spike_mask, '_spike_context'] = 'exclude_success_rate'
                logger.info(f"Marked {qb_spike_mask.sum()} QB spike plays to exclude from success rate only")
            # If both are True, keep all QB spikes (no filtering needed)
    
    return filtered_data