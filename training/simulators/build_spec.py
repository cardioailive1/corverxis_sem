"""
Authoring file for the shared simulator domain spec. Run `python3 build_spec.py` to regenerate
  training/simulators/domains_spec.json   (used by the Python simulators, GRPO dataset, eval harness)
  backend/simulators/domains_spec.json    (used by the Node simulators and the product API)
Both copies must stay identical (checked by test_spec.py and by this script).

Each domain is a hidden-cause -> noisy-signals model: every cause turns each signal on with the
probability given below (signals not listed fire at `default_p`). The probabilities are hand-set and
ILLUSTRATIVE. They are NOT estimated from real data, which matters most for cardiology and safety.
"""
import json, os, sys

def P(s):
    out = {}
    for tok in s.split():
        k, v = tok.rsplit(":", 1); out[k] = float(v)
    return out

D = []
def domain(slug, name, label, key, default_p, caution, signals, causes):
    D.append(dict(slug=slug, name=name, label=label, key=key, default_p=default_p, caution=caution,
                  signals=signals.split(), causes=[c[0] for c in causes], profiles={c[0]: P(c[1]) for c in causes}))

# ───────────────────────── industrial ─────────────────────────
domain("industrial-fault-diagnosis", "Industrial Fault Diagnosis", "industrial fault diagnosis", "failed_component", 0.04, None,
 "vibration_high temperature_high noise_abnormal rpm_unstable power_draw_high oil_pressure_low oil_contamination leak_visible output_flow_low current_imbalance intermittent_trips burning_smell sensor_reading_flatline pressure_fluctuation",
 [("bearing", "vibration_high:.9 temperature_high:.6 noise_abnormal:.8 rpm_unstable:.3 oil_contamination:.25"),
  ("belt", "vibration_high:.4 rpm_unstable:.85 noise_abnormal:.5 temperature_high:.1 output_flow_low:.25"),
  ("motor", "temperature_high:.9 rpm_unstable:.5 power_draw_high:.85 vibration_high:.2 burning_smell:.35 current_imbalance:.4"),
  ("sensor_calibration", "rpm_unstable:.2 power_draw_high:.1 vibration_high:.1 temperature_high:.15 sensor_reading_flatline:.45"),
  ("gearbox_wear", "noise_abnormal:.85 vibration_high:.6 oil_contamination:.6 temperature_high:.4 oil_pressure_low:.2"),
  ("shaft_misalignment", "vibration_high:.85 noise_abnormal:.4 temperature_high:.35 power_draw_high:.3 rpm_unstable:.15"),
  ("lubrication_failure", "oil_pressure_low:.85 temperature_high:.6 noise_abnormal:.45 vibration_high:.35 oil_contamination:.3"),
  ("pump_cavitation", "noise_abnormal:.8 pressure_fluctuation:.8 output_flow_low:.65 vibration_high:.5"),
  ("seal_leak", "leak_visible:.9 oil_pressure_low:.5 output_flow_low:.4 pressure_fluctuation:.3"),
  ("cooling_failure", "temperature_high:.9 power_draw_high:.3 intermittent_trips:.4 rpm_unstable:.1"),
  ("power_supply_fault", "intermittent_trips:.8 current_imbalance:.6 rpm_unstable:.4 power_draw_high:.3 burning_smell:.1"),
  ("controller_fault", "intermittent_trips:.6 rpm_unstable:.5 sensor_reading_flatline:.3 pressure_fluctuation:.25"),
  ("overload", "power_draw_high:.85 temperature_high:.6 current_imbalance:.3 rpm_unstable:.35 intermittent_trips:.3 vibration_high:.2"),
  ("valve_stuck", "pressure_fluctuation:.6 output_flow_low:.75 noise_abnormal:.2 leak_visible:.15")])

# ───────────────────────── medical ─────────────────────────
domain("medical-diagnostics", "Medical Diagnostics", "medical diagnostics", "condition", 0.03,
 "Decision support only. This is not a medical diagnosis. Consult a qualified clinician.",
 "fever_high cough_productive cough_dry shortness_of_breath sore_throat body_aches sneezing loss_of_taste_smell fatigue chest_pain headache nausea_vomiting diarrhea rash joint_pain wheezing",
 [("influenza", "fever_high:.85 body_aches:.9 fatigue:.8 cough_dry:.5 sore_throat:.4 sneezing:.1 loss_of_taste_smell:.05 shortness_of_breath:.15 headache:.5 joint_pain:.3"),
  ("bacterial_pneumonia", "fever_high:.9 cough_productive:.85 shortness_of_breath:.7 fatigue:.6 body_aches:.3 sore_throat:.1 sneezing:.05 loss_of_taste_smell:.05 chest_pain:.4"),
  ("covid19", "fever_high:.6 fatigue:.75 body_aches:.5 loss_of_taste_smell:.55 cough_dry:.5 shortness_of_breath:.35 sore_throat:.3 sneezing:.1 headache:.4 joint_pain:.2"),
  ("common_cold", "sneezing:.85 sore_throat:.6 cough_dry:.4 fatigue:.3 fever_high:.1 body_aches:.15 shortness_of_breath:.02 loss_of_taste_smell:.02 headache:.15"),
  ("allergic_rhinitis", "sneezing:.9 sore_throat:.15 fatigue:.2 fever_high:.01 cough_dry:.2 body_aches:.02 shortness_of_breath:.1 loss_of_taste_smell:.02 wheezing:.15"),
  ("strep_throat", "sore_throat:.9 fever_high:.6 headache:.3 nausea_vomiting:.2 body_aches:.3 cough_dry:.05 sneezing:.03"),
  ("acute_bronchitis", "cough_productive:.7 cough_dry:.5 wheezing:.35 fatigue:.4 fever_high:.2 shortness_of_breath:.25 sore_throat:.25 chest_pain:.2"),
  ("sinusitis", "headache:.65 sneezing:.35 sore_throat:.3 fever_high:.25 cough_productive:.3 fatigue:.3"),
  ("gastroenteritis", "nausea_vomiting:.85 diarrhea:.85 fever_high:.35 fatigue:.5 body_aches:.3 headache:.2"),
  ("asthma_exacerbation", "wheezing:.9 shortness_of_breath:.85 cough_dry:.6 chest_pain:.3 fatigue:.3"),
  ("migraine", "headache:.95 nausea_vomiting:.6 fatigue:.25"),
  ("mononucleosis", "fatigue:.9 sore_throat:.75 fever_high:.6 body_aches:.4 rash:.15 headache:.3"),
  ("lyme_disease", "rash:.7 joint_pain:.6 fatigue:.6 fever_high:.4 headache:.45 body_aches:.45")])

# ───────────────────────── security ─────────────────────────
domain("security-incident-investigation", "Security Incident Investigation", "security incident investigation", "attack_vector", 0.03, None,
 "unusual_login_location privilege_escalation_event outbound_data_transfer_spike known_malware_signature after_hours_access multiple_failed_logins new_admin_account_created dns_tunneling_pattern ransomware_activity unusual_process_execution lateral_movement_detected mfa_fatigue_prompts suspicious_attachment_opened web_app_error_spike cloud_storage_public_exposure",
 [("phishing_credential_theft", "unusual_login_location:.8 after_hours_access:.5 multiple_failed_logins:.15 privilege_escalation_event:.3 new_admin_account_created:.1 outbound_data_transfer_spike:.35 known_malware_signature:.05 suspicious_attachment_opened:.3 mfa_fatigue_prompts:.1"),
  ("unpatched_cve_exploit", "known_malware_signature:.7 privilege_escalation_event:.75 outbound_data_transfer_spike:.4 unusual_login_location:.2 after_hours_access:.3 multiple_failed_logins:.05 new_admin_account_created:.2 web_app_error_spike:.2 lateral_movement_detected:.4 unusual_process_execution:.4"),
  ("insider_threat", "outbound_data_transfer_spike:.75 after_hours_access:.7 unusual_login_location:.1 privilege_escalation_event:.2 new_admin_account_created:.1 multiple_failed_logins:.02 known_malware_signature:.02 cloud_storage_public_exposure:.1"),
  ("supply_chain_compromise", "known_malware_signature:.6 new_admin_account_created:.45 privilege_escalation_event:.55 outbound_data_transfer_spike:.5 unusual_login_location:.15 after_hours_access:.2 multiple_failed_logins:.03 unusual_process_execution:.5 lateral_movement_detected:.35 dns_tunneling_pattern:.2"),
  ("brute_force_login", "multiple_failed_logins:.9 unusual_login_location:.5 after_hours_access:.4 privilege_escalation_event:.1 outbound_data_transfer_spike:.1 new_admin_account_created:.05 known_malware_signature:.02 web_app_error_spike:.1 mfa_fatigue_prompts:.1"),
  ("ransomware_deployment", "ransomware_activity:.9 unusual_process_execution:.7 lateral_movement_detected:.6 known_malware_signature:.6 privilege_escalation_event:.5 after_hours_access:.4 new_admin_account_created:.3"),
  ("sql_injection", "web_app_error_spike:.8 outbound_data_transfer_spike:.5 unusual_process_execution:.15 known_malware_signature:.1 multiple_failed_logins:.05"),
  ("credential_stuffing", "multiple_failed_logins:.85 unusual_login_location:.6 after_hours_access:.3 web_app_error_spike:.2"),
  ("mfa_fatigue_attack", "mfa_fatigue_prompts:.9 unusual_login_location:.55 after_hours_access:.5 privilege_escalation_event:.2 multiple_failed_logins:.2"),
  ("dns_tunneling_exfiltration", "dns_tunneling_pattern:.9 outbound_data_transfer_spike:.6 unusual_process_execution:.4 known_malware_signature:.3"),
  ("misconfigured_cloud_storage", "cloud_storage_public_exposure:.9 outbound_data_transfer_spike:.4 unusual_login_location:.15"),
  ("malicious_macro_phishing", "suspicious_attachment_opened:.9 unusual_process_execution:.7 known_malware_signature:.45 lateral_movement_detected:.25 privilege_escalation_event:.25"),
  ("zero_day_exploit", "unusual_process_execution:.6 privilege_escalation_event:.65 lateral_movement_detected:.45 known_malware_signature:.1 outbound_data_transfer_spike:.35")])

# ───────────────────────── fraud ─────────────────────────
domain("financial-fraud-investigation", "Financial Fraud Investigation", "financial fraud investigation", "cause", 0.02, None,
 "rapid_small_transactions new_shipping_address device_fingerprint_mismatch velocity_spike high_risk_merchant_category geo_mismatch unusual_hours_activity refund_abuse_pattern round_amount_transactions multiple_accounts_same_device chargeback_history atm_withdrawals_abroad password_reset_before_transaction split_payments_below_threshold",
 [("stolen_card_testing", "rapid_small_transactions:.9 velocity_spike:.85 new_shipping_address:.2 device_fingerprint_mismatch:.3 high_risk_merchant_category:.4 geo_mismatch:.3 unusual_hours_activity:.35"),
  ("account_takeover", "device_fingerprint_mismatch:.85 geo_mismatch:.7 new_shipping_address:.6 velocity_spike:.4 rapid_small_transactions:.15 high_risk_merchant_category:.2 password_reset_before_transaction:.5 unusual_hours_activity:.3"),
  ("synthetic_identity", "new_shipping_address:.7 high_risk_merchant_category:.3 velocity_spike:.25 device_fingerprint_mismatch:.2 rapid_small_transactions:.1 geo_mismatch:.15 multiple_accounts_same_device:.4 round_amount_transactions:.15"),
  ("merchant_collusion", "high_risk_merchant_category:.8 rapid_small_transactions:.3 velocity_spike:.3 new_shipping_address:.05 device_fingerprint_mismatch:.1 geo_mismatch:.1 round_amount_transactions:.35 refund_abuse_pattern:.3"),
  ("legitimate_unusual_purchase", "new_shipping_address:.25 geo_mismatch:.2 velocity_spike:.1 high_risk_merchant_category:.1 rapid_small_transactions:.03 device_fingerprint_mismatch:.05 round_amount_transactions:.1"),
  ("friendly_fraud_chargeback", "chargeback_history:.8 high_risk_merchant_category:.1 new_shipping_address:.1 device_fingerprint_mismatch:.05"),
  ("money_mule_activity", "multiple_accounts_same_device:.55 round_amount_transactions:.5 velocity_spike:.45 rapid_small_transactions:.4 atm_withdrawals_abroad:.2 new_shipping_address:.1"),
  ("structuring_smurfing", "split_payments_below_threshold:.9 round_amount_transactions:.6 rapid_small_transactions:.4 velocity_spike:.35"),
  ("refund_abuse", "refund_abuse_pattern:.9 chargeback_history:.3 new_shipping_address:.3 velocity_spike:.1"),
  ("carding_bin_attack", "rapid_small_transactions:.8 velocity_spike:.75 unusual_hours_activity:.5 device_fingerprint_mismatch:.4 high_risk_merchant_category:.3"),
  ("sim_swap_takeover", "password_reset_before_transaction:.8 device_fingerprint_mismatch:.7 geo_mismatch:.45 new_shipping_address:.4 unusual_hours_activity:.35"),
  ("insider_fraud", "unusual_hours_activity:.6 round_amount_transactions:.4 split_payments_below_threshold:.35 multiple_accounts_same_device:.3"),
  ("card_skimming_abroad", "atm_withdrawals_abroad:.8 geo_mismatch:.75 rapid_small_transactions:.25 device_fingerprint_mismatch:.1")])

# ───────────────────────── scientific ─────────────────────────
domain("scientific-discovery", "Scientific Discovery", "scientific discovery", "mechanism", 0.05, None,
 "result_reproducible correlates_with_control_variable effect_size_large dose_response_relationship instrument_calibration_drift replicates_in_independent_lab small_sample_size outliers_drive_result batch_effect_pattern effect_shrinks_with_larger_sample time_trend_in_data reagent_lot_change selective_reporting_signs",
 [("catalyst_effect", "dose_response_relationship:.85 result_reproducible:.8 effect_size_large:.6 correlates_with_control_variable:.1 instrument_calibration_drift:.05 replicates_in_independent_lab:.6"),
  ("confounding_variable", "correlates_with_control_variable:.9 result_reproducible:.6 dose_response_relationship:.3 effect_size_large:.4 instrument_calibration_drift:.1 replicates_in_independent_lab:.3"),
  ("measurement_artifact", "instrument_calibration_drift:.85 result_reproducible:.2 correlates_with_control_variable:.15 dose_response_relationship:.1 effect_size_large:.3 replicates_in_independent_lab:.1 time_trend_in_data:.3"),
  ("genuine_novel_effect", "result_reproducible:.9 dose_response_relationship:.7 effect_size_large:.55 correlates_with_control_variable:.05 instrument_calibration_drift:.03 replicates_in_independent_lab:.8"),
  ("temperature_dependency", "dose_response_relationship:.5 result_reproducible:.75 correlates_with_control_variable:.4 effect_size_large:.35 instrument_calibration_drift:.1 time_trend_in_data:.3"),
  ("p_hacking", "selective_reporting_signs:.9 effect_shrinks_with_larger_sample:.5 replicates_in_independent_lab:.05 result_reproducible:.15 effect_size_large:.4 small_sample_size:.4"),
  ("batch_effect", "batch_effect_pattern:.9 reagent_lot_change:.5 result_reproducible:.3 replicates_in_independent_lab:.15 time_trend_in_data:.3"),
  ("small_sample_noise", "small_sample_size:.9 effect_shrinks_with_larger_sample:.7 result_reproducible:.15 effect_size_large:.5 outliers_drive_result:.3"),
  ("regression_to_the_mean", "effect_shrinks_with_larger_sample:.6 result_reproducible:.25 effect_size_large:.35 time_trend_in_data:.4 selective_reporting_signs:.2"),
  ("outlier_driven_artifact", "outliers_drive_result:.9 small_sample_size:.4 result_reproducible:.2 effect_size_large:.5 dose_response_relationship:.1"),
  ("reagent_contamination", "reagent_lot_change:.8 batch_effect_pattern:.45 result_reproducible:.25 instrument_calibration_drift:.15"),
  ("selection_bias", "correlates_with_control_variable:.55 selective_reporting_signs:.4 replicates_in_independent_lab:.1 result_reproducible:.35 effect_size_large:.4"),
  ("seasonal_or_time_drift", "time_trend_in_data:.9 correlates_with_control_variable:.3 result_reproducible:.35 instrument_calibration_drift:.3 batch_effect_pattern:.2")])

# ───────────────────────── production ─────────────────────────
domain("production-incident-rootcause", "Production Incident Root-Causing", "production incident root-causing", "root_cause", 0.03, None,
 "error_rate_spike latency_increase deploy_within_last_hour database_timeout_errors cpu_usage_high memory_usage_climbing upstream_5xx_errors disk_usage_high certificate_expiry_warning dns_resolution_failures config_change_recent queue_backlog_growing cache_hit_rate_drop thread_pool_saturation region_specific_errors",
 [("bad_deploy", "deploy_within_last_hour:.9 error_rate_spike:.75 latency_increase:.4 upstream_5xx_errors:.3 database_timeout_errors:.15 cpu_usage_high:.2 memory_usage_climbing:.1"),
  ("database_connection_pool_exhaustion", "database_timeout_errors:.9 latency_increase:.7 error_rate_spike:.5 deploy_within_last_hour:.1 cpu_usage_high:.2 memory_usage_climbing:.15 upstream_5xx_errors:.1 thread_pool_saturation:.4"),
  ("third_party_api_outage", "upstream_5xx_errors:.85 latency_increase:.6 error_rate_spike:.55 deploy_within_last_hour:.05 database_timeout_errors:.1 cpu_usage_high:.1 memory_usage_climbing:.05 queue_backlog_growing:.2"),
  ("traffic_spike_ddos", "cpu_usage_high:.85 latency_increase:.75 error_rate_spike:.6 database_timeout_errors:.3 memory_usage_climbing:.2 deploy_within_last_hour:.05 upstream_5xx_errors:.15 thread_pool_saturation:.4"),
  ("memory_leak", "memory_usage_climbing:.9 latency_increase:.5 error_rate_spike:.35 cpu_usage_high:.25 deploy_within_last_hour:.1 database_timeout_errors:.1 upstream_5xx_errors:.05"),
  ("disk_full", "disk_usage_high:.95 error_rate_spike:.55 database_timeout_errors:.3 latency_increase:.3 queue_backlog_growing:.2"),
  ("expired_certificate", "certificate_expiry_warning:.85 error_rate_spike:.7 upstream_5xx_errors:.4 latency_increase:.1"),
  ("dns_failure", "dns_resolution_failures:.9 error_rate_spike:.6 upstream_5xx_errors:.5 latency_increase:.4 region_specific_errors:.2"),
  ("bad_config_push", "config_change_recent:.9 error_rate_spike:.6 latency_increase:.3 deploy_within_last_hour:.25 upstream_5xx_errors:.2"),
  ("message_queue_backlog", "queue_backlog_growing:.9 latency_increase:.5 memory_usage_climbing:.3 error_rate_spike:.2 cpu_usage_high:.2"),
  ("cache_stampede", "cache_hit_rate_drop:.9 database_timeout_errors:.6 latency_increase:.65 cpu_usage_high:.4 error_rate_spike:.35"),
  ("thread_pool_exhaustion", "thread_pool_saturation:.9 latency_increase:.7 error_rate_spike:.4 cpu_usage_high:.3 database_timeout_errors:.2"),
  ("regional_cloud_outage", "region_specific_errors:.9 upstream_5xx_errors:.5 error_rate_spike:.55 latency_increase:.5 dns_resolution_failures:.2"),
  ("dependency_version_conflict", "deploy_within_last_hour:.6 error_rate_spike:.5 memory_usage_climbing:.2 config_change_recent:.2 cache_hit_rate_drop:.1")])

# ───────────────────────── cardiology ─────────────────────────
domain("cardiology-ecg-review", "Cardiology & ECG Review", "cardiology and ECG review", "cardiac_condition", 0.03,
 "Illustrative simulator only. Not clinically validated and not a diagnosis. Chest pain, fainting or a fast or irregular heartbeat can be emergencies: seek urgent medical care.",
 "chest_pain_exertional chest_pain_at_rest chest_pain_positional shortness_of_breath palpitations syncope leg_swelling diaphoresis st_elevation st_depression t_wave_inversion irregular_rr_intervals absent_p_waves wide_qrs prolonged_qt elevated_troponin tachycardia bradycardia",
 [("stemi", "chest_pain_at_rest:.85 st_elevation:.95 elevated_troponin:.9 diaphoresis:.6 shortness_of_breath:.4 tachycardia:.3 bradycardia:.15 t_wave_inversion:.2 syncope:.1"),
  ("nstemi", "chest_pain_at_rest:.7 st_depression:.6 t_wave_inversion:.5 elevated_troponin:.9 diaphoresis:.4 shortness_of_breath:.4 tachycardia:.25"),
  ("unstable_angina", "chest_pain_at_rest:.75 st_depression:.5 t_wave_inversion:.4 elevated_troponin:.05 diaphoresis:.25 shortness_of_breath:.3"),
  ("stable_angina", "chest_pain_exertional:.9 st_depression:.3 shortness_of_breath:.3 elevated_troponin:.02 diaphoresis:.1"),
  ("atrial_fibrillation", "irregular_rr_intervals:.95 absent_p_waves:.9 palpitations:.7 tachycardia:.55 shortness_of_breath:.35 syncope:.1 leg_swelling:.1"),
  ("ventricular_tachycardia", "wide_qrs:.9 tachycardia:.95 palpitations:.6 syncope:.5 shortness_of_breath:.4 chest_pain_at_rest:.2 elevated_troponin:.15"),
  ("supraventricular_tachycardia", "tachycardia:.95 palpitations:.85 shortness_of_breath:.2 syncope:.1 chest_pain_at_rest:.15"),
  ("complete_heart_block", "bradycardia:.9 syncope:.6 wide_qrs:.4 shortness_of_breath:.3 diaphoresis:.1"),
  ("long_qt_syndrome", "prolonged_qt:.9 syncope:.55 palpitations:.45 tachycardia:.2"),
  ("heart_failure_decompensation", "shortness_of_breath:.9 leg_swelling:.8 tachycardia:.45 irregular_rr_intervals:.25 absent_p_waves:.2 wide_qrs:.3 elevated_troponin:.25 t_wave_inversion:.2"),
  ("pericarditis", "chest_pain_positional:.85 chest_pain_at_rest:.5 st_elevation:.6 tachycardia:.3 shortness_of_breath:.2 elevated_troponin:.2 t_wave_inversion:.3"),
  ("pulmonary_embolism", "shortness_of_breath:.85 tachycardia:.7 chest_pain_positional:.45 leg_swelling:.35 elevated_troponin:.3 t_wave_inversion:.25 syncope:.2 st_depression:.1"),
  ("aortic_stenosis", "shortness_of_breath:.55 chest_pain_exertional:.45 syncope:.4 leg_swelling:.1 palpitations:.1"),
  ("vasovagal_syncope", "syncope:.9 diaphoresis:.5 bradycardia:.4 palpitations:.1")])

# ───────────────────────── network ─────────────────────────
domain("network-infrastructure-outage", "Network & Infrastructure Outage", "network and infrastructure outage diagnosis", "failure_point", 0.03, None,
 "packet_loss_high latency_spike dns_resolution_failures bgp_route_flaps interface_crc_errors link_down_alarm router_cpu_high connection_resets certificate_errors dhcp_exhaustion_alerts radius_auth_failures throughput_saturated single_site_affected intermittent_connectivity firewall_deny_spike power_alarm_at_site",
 [("fiber_cut", "link_down_alarm:.9 packet_loss_high:.6 single_site_affected:.6 bgp_route_flaps:.35 intermittent_connectivity:.1"),
  ("bgp_misconfiguration", "bgp_route_flaps:.8 packet_loss_high:.5 latency_spike:.4 router_cpu_high:.3 connection_resets:.3"),
  ("dns_server_failure", "dns_resolution_failures:.95 connection_resets:.3 latency_spike:.25 certificate_errors:.1"),
  ("ddos_volumetric", "throughput_saturated:.9 packet_loss_high:.7 latency_spike:.7 router_cpu_high:.5 firewall_deny_spike:.6"),
  ("failing_switch_hardware", "interface_crc_errors:.6 intermittent_connectivity:.7 packet_loss_high:.45 single_site_affected:.3 link_down_alarm:.3"),
  ("bad_cable_or_duplex_mismatch", "interface_crc_errors:.85 packet_loss_high:.4 latency_spike:.3 intermittent_connectivity:.4 throughput_saturated:.1"),
  ("dhcp_pool_exhaustion", "dhcp_exhaustion_alerts:.9 intermittent_connectivity:.3 single_site_affected:.45 dns_resolution_failures:.05"),
  ("expired_tls_certificate", "certificate_errors:.95 connection_resets:.5 latency_spike:.05"),
  ("firewall_rule_misconfiguration", "firewall_deny_spike:.8 connection_resets:.6 packet_loss_high:.1 single_site_affected:.25 intermittent_connectivity:.15"),
  ("link_saturation", "throughput_saturated:.9 latency_spike:.7 packet_loss_high:.5 router_cpu_high:.2"),
  ("spanning_tree_loop", "packet_loss_high:.7 router_cpu_high:.6 throughput_saturated:.5 intermittent_connectivity:.5 interface_crc_errors:.15 single_site_affected:.4"),
  ("radius_auth_outage", "radius_auth_failures:.95 connection_resets:.2 single_site_affected:.2"),
  ("power_failure_at_site", "power_alarm_at_site:.9 link_down_alarm:.7 single_site_affected:.85 packet_loss_high:.3"),
  ("router_cpu_overload", "router_cpu_high:.9 latency_spike:.6 packet_loss_high:.4 bgp_route_flaps:.35 connection_resets:.2")])

# ───────────────────────── supply chain ─────────────────────────
domain("supply-chain-disruption", "Supply Chain & Logistics", "supply chain disruption analysis", "disruption_cause", 0.03, None,
 "supplier_lead_time_increase stockout_alerts port_congestion_reports customs_hold_notices demand_spike_vs_forecast supplier_quality_rejects single_supplier_dependency freight_rate_surge weather_alert_on_route labor_strike_notice inventory_record_mismatch supplier_order_cancellations currency_swing regulatory_change_notice carrier_capacity_shortage input_price_spike",
 [("supplier_insolvency", "supplier_order_cancellations:.75 supplier_lead_time_increase:.6 single_supplier_dependency:.5 stockout_alerts:.5 supplier_quality_rejects:.2"),
  ("port_congestion", "port_congestion_reports:.9 supplier_lead_time_increase:.6 freight_rate_surge:.55 stockout_alerts:.35 carrier_capacity_shortage:.3"),
  ("customs_delay", "customs_hold_notices:.9 supplier_lead_time_increase:.5 regulatory_change_notice:.3 stockout_alerts:.3"),
  ("demand_shock", "demand_spike_vs_forecast:.9 stockout_alerts:.75 supplier_lead_time_increase:.3 freight_rate_surge:.25 input_price_spike:.2"),
  ("supplier_quality_failure", "supplier_quality_rejects:.9 stockout_alerts:.4 supplier_lead_time_increase:.3 supplier_order_cancellations:.15"),
  ("natural_disaster_on_route", "weather_alert_on_route:.9 supplier_lead_time_increase:.6 carrier_capacity_shortage:.35 freight_rate_surge:.4 port_congestion_reports:.2"),
  ("labor_strike", "labor_strike_notice:.9 port_congestion_reports:.4 supplier_lead_time_increase:.55 carrier_capacity_shortage:.3"),
  ("carrier_capacity_crunch", "carrier_capacity_shortage:.9 freight_rate_surge:.8 supplier_lead_time_increase:.3 stockout_alerts:.2"),
  ("forecasting_error", "demand_spike_vs_forecast:.55 stockout_alerts:.6 inventory_record_mismatch:.25 supplier_lead_time_increase:.05"),
  ("inventory_record_error", "inventory_record_mismatch:.9 stockout_alerts:.5 demand_spike_vs_forecast:.05"),
  ("regulatory_change", "regulatory_change_notice:.9 customs_hold_notices:.5 supplier_lead_time_increase:.3 supplier_order_cancellations:.15"),
  ("currency_shock", "currency_swing:.9 input_price_spike:.5 supplier_order_cancellations:.2 freight_rate_surge:.15"),
  ("raw_material_shortage", "input_price_spike:.85 supplier_lead_time_increase:.6 stockout_alerts:.45 supplier_order_cancellations:.3 single_supplier_dependency:.3")])

# ───────────────────────── safety ─────────────────────────
domain("safety-incident-analysis", "Energy, Mining & Aviation Safety", "energy, mining and aviation safety incident analysis", "incident_cause", 0.03,
 "Illustrative simulator only. Not a substitute for a qualified investigation or the applicable safety regulations.",
 "gas_detector_alarm pressure_exceedance equipment_vibration_anomaly operator_fatigue_reported procedure_not_followed maintenance_overdue ground_movement_detected visibility_poor loss_of_communication fire_or_smoke_alarm electrical_arcing_or_trip load_or_fuel_imbalance alarm_silenced_or_ignored recent_shift_change noise_before_failure sensor_disagreement",
 [("methane_accumulation", "gas_detector_alarm:.9 fire_or_smoke_alarm:.3 alarm_silenced_or_ignored:.3 electrical_arcing_or_trip:.2 sensor_disagreement:.2"),
  ("roof_or_slope_failure", "ground_movement_detected:.9 noise_before_failure:.5 loss_of_communication:.15 equipment_vibration_anomaly:.2"),
  ("equipment_mechanical_failure", "equipment_vibration_anomaly:.75 noise_before_failure:.7 maintenance_overdue:.55 pressure_exceedance:.2 fire_or_smoke_alarm:.15"),
  ("human_fatigue_error", "operator_fatigue_reported:.85 recent_shift_change:.5 procedure_not_followed:.5 alarm_silenced_or_ignored:.35"),
  ("procedure_violation", "procedure_not_followed:.9 alarm_silenced_or_ignored:.4 operator_fatigue_reported:.2 recent_shift_change:.2"),
  ("maintenance_lapse", "maintenance_overdue:.9 equipment_vibration_anomaly:.4 noise_before_failure:.35 sensor_disagreement:.2"),
  ("electrical_fault_ignition", "electrical_arcing_or_trip:.85 fire_or_smoke_alarm:.7 gas_detector_alarm:.2 maintenance_overdue:.25"),
  ("pressure_vessel_overpressure", "pressure_exceedance:.9 sensor_disagreement:.3 alarm_silenced_or_ignored:.3 noise_before_failure:.25 maintenance_overdue:.2"),
  ("communication_breakdown", "loss_of_communication:.9 recent_shift_change:.4 procedure_not_followed:.3 visibility_poor:.1"),
  ("weather_visibility_event", "visibility_poor:.9 loss_of_communication:.2 load_or_fuel_imbalance:.1"),
  ("fuel_or_load_management_error", "load_or_fuel_imbalance:.9 operator_fatigue_reported:.2 sensor_disagreement:.25 procedure_not_followed:.2"),
  ("misleading_sensor_failure", "sensor_disagreement:.9 alarm_silenced_or_ignored:.3 maintenance_overdue:.3 pressure_exceedance:.1"),
  ("alarm_fatigue_normalisation", "alarm_silenced_or_ignored:.9 operator_fatigue_reported:.4 procedure_not_followed:.35 gas_detector_alarm:.15 pressure_exceedance:.15"),
  ("ventilation_failure", "gas_detector_alarm:.55 equipment_vibration_anomaly:.3 operator_fatigue_reported:.3 pressure_exceedance:.2 electrical_arcing_or_trip:.2")])


# ───────────────────────── education ─────────────────────────
domain("education-learning-support", "Education & Learning Support", "learning difficulty analysis", "learning_barrier", 0.03,
 "Decision support for educators. Not a diagnosis of any learning disability. Involve qualified specialists and the family.",
 "low_quiz_scores strong_oral_but_weak_written struggles_with_prerequisite_topics test_day_underperformance frequent_absences falls_asleep_in_class off_task_behavior reading_fluency_low slow_writing_speed avoids_math_tasks disengaged_from_homework strong_in_some_subjects_only social_withdrawal difficulty_following_instructions finishes_work_early squinting_or_asking_to_repeat",
 [("prerequisite_knowledge_gap", "struggles_with_prerequisite_topics:.9 low_quiz_scores:.7 avoids_math_tasks:.35 disengaged_from_homework:.3 strong_in_some_subjects_only:.4"),
  ("test_anxiety", "test_day_underperformance:.9 avoids_math_tasks:.2 strong_oral_but_weak_written:.25 low_quiz_scores:.3 social_withdrawal:.15"),
  ("attention_difficulty", "off_task_behavior:.85 difficulty_following_instructions:.7 disengaged_from_homework:.5 low_quiz_scores:.4 test_day_underperformance:.2"),
  ("dyslexia_like_reading_pattern", "reading_fluency_low:.9 strong_oral_but_weak_written:.7 slow_writing_speed:.5 low_quiz_scores:.4 strong_in_some_subjects_only:.5 disengaged_from_homework:.3"),
  ("math_anxiety", "avoids_math_tasks:.9 test_day_underperformance:.55 low_quiz_scores:.4 strong_in_some_subjects_only:.45 disengaged_from_homework:.25"),
  ("low_motivation", "disengaged_from_homework:.85 off_task_behavior:.5 frequent_absences:.3 low_quiz_scores:.45 social_withdrawal:.2"),
  ("sleep_deprivation", "falls_asleep_in_class:.9 off_task_behavior:.4 frequent_absences:.3 low_quiz_scores:.35 difficulty_following_instructions:.3"),
  ("language_barrier", "difficulty_following_instructions:.7 strong_oral_but_weak_written:.35 reading_fluency_low:.5 low_quiz_scores:.5 social_withdrawal:.35 strong_in_some_subjects_only:.45"),
  ("ineffective_study_methods", "low_quiz_scores:.65 test_day_underperformance:.4 disengaged_from_homework:.2 struggles_with_prerequisite_topics:.3"),
  ("social_stress_or_bullying", "social_withdrawal:.8 frequent_absences:.55 falls_asleep_in_class:.2 off_task_behavior:.3 low_quiz_scores:.35 disengaged_from_homework:.4"),
  ("under_challenged", "finishes_work_early:.85 off_task_behavior:.5 disengaged_from_homework:.5 strong_in_some_subjects_only:.4 low_quiz_scores:.1"),
  ("pacing_too_fast", "low_quiz_scores:.55 struggles_with_prerequisite_topics:.4 difficulty_following_instructions:.5 disengaged_from_homework:.35 test_day_underperformance:.2"),
  ("vision_or_hearing_difficulty", "squinting_or_asking_to_repeat:.85 difficulty_following_instructions:.5 reading_fluency_low:.35 off_task_behavior:.3 low_quiz_scores:.35"),
  ("handwriting_motor_difficulty", "slow_writing_speed:.85 strong_oral_but_weak_written:.55 low_quiz_scores:.3")])

# ───────────────────────── AI & ML ─────────────────────────
domain("ai-ml-system-failures", "AI & ML Systems", "AI and machine learning failure diagnosis", "failure_cause", 0.03, None,
 "train_loss_low_val_loss_high train_loss_plateau_high loss_nan_or_exploding accuracy_drop_after_deploy suspiciously_high_eval_score errors_concentrated_in_minority_class performance_varies_by_subgroup input_feature_distribution_shift outputs_unsupported_by_sources retrieval_returns_irrelevant_docs gradient_norm_vanishing latency_regression accuracy_drop_after_quantization output_format_violations sensitive_to_prompt_wording label_disagreement_among_annotators",
 [("overfitting", "train_loss_low_val_loss_high:.9 accuracy_drop_after_deploy:.4 performance_varies_by_subgroup:.2 sensitive_to_prompt_wording:.2"),
  ("underfitting_or_low_capacity", "train_loss_plateau_high:.9 gradient_norm_vanishing:.25"),
  ("learning_rate_instability", "loss_nan_or_exploding:.85 train_loss_plateau_high:.3 gradient_norm_vanishing:.15"),
  ("data_leakage", "suspiciously_high_eval_score:.9 accuracy_drop_after_deploy:.75 train_loss_low_val_loss_high:.15"),
  ("covariate_shift", "input_feature_distribution_shift:.9 accuracy_drop_after_deploy:.75 performance_varies_by_subgroup:.3"),
  ("label_noise", "label_disagreement_among_annotators:.85 train_loss_plateau_high:.4 train_loss_low_val_loss_high:.25"),
  ("class_imbalance", "errors_concentrated_in_minority_class:.9 performance_varies_by_subgroup:.45"),
  ("rag_retrieval_failure", "retrieval_returns_irrelevant_docs:.9 outputs_unsupported_by_sources:.75"),
  ("ungrounded_hallucination", "outputs_unsupported_by_sources:.85 sensitive_to_prompt_wording:.3"),
  ("vanishing_gradients", "gradient_norm_vanishing:.9 train_loss_plateau_high:.6"),
  ("quantization_degradation", "accuracy_drop_after_quantization:.9 output_format_violations:.2 accuracy_drop_after_deploy:.3"),
  ("prompt_brittleness", "sensitive_to_prompt_wording:.9 output_format_violations:.5 performance_varies_by_subgroup:.2"),
  ("train_serving_skew", "accuracy_drop_after_deploy:.8 input_feature_distribution_shift:.55 latency_regression:.15"),
  ("biased_training_data", "performance_varies_by_subgroup:.9 errors_concentrated_in_minority_class:.55 label_disagreement_among_annotators:.2"),
  ("inference_infra_regression", "latency_regression:.9 output_format_violations:.2 accuracy_drop_after_deploy:.15")])

# ───────────────────────── robotics ─────────────────────────
domain("robotics-fault-diagnosis", "Robots & Robotics", "robot fault diagnosis", "fault_cause", 0.03, None,
 "joint_torque_spike encoder_drift localization_jump motor_overheat collision_detected gripper_slip path_oscillation battery_voltage_sag lidar_dropout comms_latency_high calibration_offset_in_pick estop_triggered vision_pose_error payload_near_rating wheel_or_foot_slip",
 [("encoder_fault", "encoder_drift:.85 localization_jump:.35 path_oscillation:.4 joint_torque_spike:.3"),
  ("motor_overload_or_overheat", "motor_overheat:.9 joint_torque_spike:.5 payload_near_rating:.5 battery_voltage_sag:.25"),
  ("gripper_wear", "gripper_slip:.85 calibration_offset_in_pick:.35 payload_near_rating:.2"),
  ("localization_failure", "localization_jump:.9 path_oscillation:.5 lidar_dropout:.45 vision_pose_error:.3 wheel_or_foot_slip:.3"),
  ("lidar_obstruction_or_failure", "lidar_dropout:.9 localization_jump:.5 collision_detected:.35 estop_triggered:.3"),
  ("battery_degradation", "battery_voltage_sag:.9 motor_overheat:.2 estop_triggered:.3"),
  ("comms_network_issue", "comms_latency_high:.9 path_oscillation:.35 estop_triggered:.3 vision_pose_error:.15"),
  ("calibration_drift", "calibration_offset_in_pick:.9 vision_pose_error:.55 encoder_drift:.3"),
  ("camera_or_vision_error", "vision_pose_error:.9 calibration_offset_in_pick:.55 gripper_slip:.2 collision_detected:.2"),
  ("controller_tuning_poor", "path_oscillation:.85 joint_torque_spike:.4 motor_overheat:.2"),
  ("surface_or_traction_loss", "wheel_or_foot_slip:.9 localization_jump:.35 path_oscillation:.3 collision_detected:.15"),
  ("payload_overload", "payload_near_rating:.9 joint_torque_spike:.6 motor_overheat:.5 gripper_slip:.35 battery_voltage_sag:.3"),
  ("unexpected_obstacle_collision", "collision_detected:.9 estop_triggered:.7 joint_torque_spike:.5"),
  ("safety_scanner_false_trip", "estop_triggered:.8 lidar_dropout:.2 collision_detected:.1")])

# ───────────────────────── process industries ─────────────────────────
domain("process-plant-operations", "Process Industries", "process plant upset diagnosis", "upset_cause", 0.03,
 "Decision support only. Follow the plant's operating procedures and involve a qualified process engineer for any safety-relevant action.",
 "temperature_deviation pressure_deviation flow_rate_low ph_out_of_range composition_off_spec foaming_observed heat_transfer_efficiency_falling valve_position_vs_flow_mismatch cooling_water_temp_high level_oscillation pump_vibration_high analyzer_reading_drift feedstock_quality_variation batch_cycle_time_longer instrument_air_pressure_low",
 [("heat_exchanger_fouling", "heat_transfer_efficiency_falling:.9 temperature_deviation:.5 pressure_deviation:.35 batch_cycle_time_longer:.4 flow_rate_low:.2"),
  ("control_valve_stiction", "valve_position_vs_flow_mismatch:.85 level_oscillation:.6 flow_rate_low:.3 temperature_deviation:.2"),
  ("catalyst_deactivation", "composition_off_spec:.7 batch_cycle_time_longer:.5 temperature_deviation:.4 heat_transfer_efficiency_falling:.1"),
  ("pump_wear", "pump_vibration_high:.85 flow_rate_low:.6 pressure_deviation:.4"),
  ("feed_composition_change", "feedstock_quality_variation:.9 composition_off_spec:.6 ph_out_of_range:.3 batch_cycle_time_longer:.3"),
  ("analyzer_drift", "analyzer_reading_drift:.9 composition_off_spec:.35 ph_out_of_range:.2"),
  ("cooling_water_loss", "cooling_water_temp_high:.9 temperature_deviation:.7 pressure_deviation:.4"),
  ("instrument_air_loss", "instrument_air_pressure_low:.9 valve_position_vs_flow_mismatch:.6 flow_rate_low:.3 level_oscillation:.2"),
  ("level_sensor_fault", "level_oscillation:.6 valve_position_vs_flow_mismatch:.2 pump_vibration_high:.1"),
  ("poor_controller_tuning", "level_oscillation:.6 temperature_deviation:.45 pressure_deviation:.4 flow_rate_low:.1"),
  ("line_leak", "pressure_deviation:.7 flow_rate_low:.7 level_oscillation:.2"),
  ("agitator_failure", "composition_off_spec:.55 temperature_deviation:.35 pump_vibration_high:.25 batch_cycle_time_longer:.55 ph_out_of_range:.3"),
  ("contamination_event", "ph_out_of_range:.6 composition_off_spec:.7 foaming_observed:.45 feedstock_quality_variation:.3"),
  ("foaming_event", "foaming_observed:.9 level_oscillation:.4 flow_rate_low:.2 composition_off_spec:.25")])

# ───────────────────────── manufacturing ─────────────────────────
domain("manufacturing-quality", "Manufacturing & Quality", "manufacturing defect root-cause analysis", "defect_cause", 0.03, None,
 "dimension_out_of_tolerance surface_scratches_or_burrs cycle_time_increase tool_wear_indicator_high material_lot_changed operator_or_shift_changed ambient_humidity_high machine_vibration_high defects_cluster_in_one_fixture coolant_concentration_off machine_temperature_drift rework_rate_rising defects_cluster_in_one_cavity gauge_readings_inconsistent intermittent_defects",
 [("tool_wear", "tool_wear_indicator_high:.9 dimension_out_of_tolerance:.7 surface_scratches_or_burrs:.6 cycle_time_increase:.2 machine_vibration_high:.3"),
  ("fixture_misalignment", "defects_cluster_in_one_fixture:.9 dimension_out_of_tolerance:.6 rework_rate_rising:.4"),
  ("material_lot_variation", "material_lot_changed:.9 dimension_out_of_tolerance:.4 surface_scratches_or_burrs:.3 rework_rate_rising:.4 intermittent_defects:.3"),
  ("thermal_drift", "machine_temperature_drift:.9 dimension_out_of_tolerance:.55 ambient_humidity_high:.2 intermittent_defects:.3"),
  ("operator_error", "operator_or_shift_changed:.8 intermittent_defects:.5 rework_rate_rising:.4 cycle_time_increase:.2"),
  ("coolant_degradation", "coolant_concentration_off:.9 surface_scratches_or_burrs:.4 tool_wear_indicator_high:.35 machine_temperature_drift:.3"),
  ("mold_cavity_damage", "defects_cluster_in_one_cavity:.9 surface_scratches_or_burrs:.45 rework_rate_rising:.4"),
  ("program_or_offset_error", "dimension_out_of_tolerance:.85 operator_or_shift_changed:.2 cycle_time_increase:.15"),
  ("gauge_calibration_error", "gauge_readings_inconsistent:.9 dimension_out_of_tolerance:.35 rework_rate_rising:.25 intermittent_defects:.3"),
  ("humidity_effect", "ambient_humidity_high:.9 intermittent_defects:.45 dimension_out_of_tolerance:.25"),
  ("spindle_bearing_wear", "machine_vibration_high:.85 surface_scratches_or_burrs:.5 dimension_out_of_tolerance:.45 cycle_time_increase:.15 machine_temperature_drift:.35"),
  ("lubrication_failure", "machine_vibration_high:.4 machine_temperature_drift:.45 cycle_time_increase:.4 tool_wear_indicator_high:.3"),
  ("supplier_process_change", "material_lot_changed:.6 dimension_out_of_tolerance:.35 rework_rate_rising:.45 intermittent_defects:.35"),
  ("worn_die_or_press", "surface_scratches_or_burrs:.75 dimension_out_of_tolerance:.5 defects_cluster_in_one_cavity:.2 machine_vibration_high:.3")])

# ───────────────────────── spacecraft ─────────────────────────
domain("spacecraft-operations", "Spacecraft Operations", "spacecraft anomaly investigation", "anomaly_cause", 0.03,
 "Illustrative simulator only. Not flight-qualified. Real anomaly response follows the mission's flight rules and engineering review.",
 "bus_voltage_drop battery_temperature_high attitude_error_growing reaction_wheel_current_high star_tracker_dropout solar_array_power_low thermal_gradient_anomaly comms_link_margin_low telemetry_gaps safe_mode_entry processor_resets propellant_pressure_drop gyro_bias_drift sun_sensor_disagreement radiation_event_flag occurs_at_eclipse_transition",
 [("solar_array_degradation", "solar_array_power_low:.9 bus_voltage_drop:.45 battery_temperature_high:.1"),
  ("battery_cell_failure", "battery_temperature_high:.75 bus_voltage_drop:.7 occurs_at_eclipse_transition:.4 safe_mode_entry:.3"),
  ("reaction_wheel_friction", "reaction_wheel_current_high:.9 attitude_error_growing:.55 safe_mode_entry:.25"),
  ("star_tracker_blinding", "star_tracker_dropout:.9 attitude_error_growing:.5 sun_sensor_disagreement:.3 safe_mode_entry:.3"),
  ("gyro_drift", "gyro_bias_drift:.9 attitude_error_growing:.6 star_tracker_dropout:.1"),
  ("single_event_upset", "radiation_event_flag:.8 processor_resets:.7 safe_mode_entry:.55 telemetry_gaps:.3"),
  ("thruster_leak", "propellant_pressure_drop:.9 attitude_error_growing:.5 reaction_wheel_current_high:.4"),
  ("thermal_control_failure", "thermal_gradient_anomaly:.9 battery_temperature_high:.45 safe_mode_entry:.25"),
  ("antenna_pointing_error", "comms_link_margin_low:.9 telemetry_gaps:.5 attitude_error_growing:.25"),
  ("power_regulator_fault", "bus_voltage_drop:.85 processor_resets:.4 telemetry_gaps:.3 safe_mode_entry:.4"),
  ("flight_software_bug", "processor_resets:.7 safe_mode_entry:.6 telemetry_gaps:.3 attitude_error_growing:.15"),
  ("ground_command_error", "safe_mode_entry:.5 attitude_error_growing:.35 telemetry_gaps:.1 comms_link_margin_low:.1"),
  ("eclipse_transition_transient", "occurs_at_eclipse_transition:.9 bus_voltage_drop:.5 thermal_gradient_anomaly:.35 solar_array_power_low:.3"),
  ("debris_or_micrometeoroid_hit", "attitude_error_growing:.5 bus_voltage_drop:.3 telemetry_gaps:.3 sun_sensor_disagreement:.25 propellant_pressure_drop:.2 safe_mode_entry:.45 solar_array_power_low:.25")])

# ───────────────────────── financial markets ─────────────────────────
domain("financial-markets-analysis", "Financial Markets", "financial market move analysis", "market_driver", 0.03,
 "Educational analysis of what may explain a market move. Not financial advice and not a trading signal.",
 "price_gap_at_open volume_spike volatility_index_jump bid_ask_spread_widening sector_wide_move company_specific_headline central_bank_announcement earnings_release_today order_book_thin options_expiry_day index_rebalance_day correlated_assets_selling_off circuit_breaker_triggered currency_move_large credit_spreads_widening",
 [("earnings_surprise", "earnings_release_today:.9 company_specific_headline:.6 price_gap_at_open:.7 volume_spike:.75"),
  ("central_bank_surprise", "central_bank_announcement:.9 volatility_index_jump:.6 currency_move_large:.5 sector_wide_move:.4 credit_spreads_widening:.25"),
  ("macro_data_surprise", "volatility_index_jump:.4 currency_move_large:.35 sector_wide_move:.4 price_gap_at_open:.35 volume_spike:.4"),
  ("liquidity_crunch", "bid_ask_spread_widening:.85 order_book_thin:.8 volatility_index_jump:.5 correlated_assets_selling_off:.4 credit_spreads_widening:.35"),
  ("short_squeeze", "volume_spike:.85 price_gap_at_open:.4 company_specific_headline:.25 bid_ask_spread_widening:.3 order_book_thin:.3"),
  ("algorithmic_flash_crash", "circuit_breaker_triggered:.6 order_book_thin:.6 bid_ask_spread_widening:.6 volume_spike:.6 volatility_index_jump:.4"),
  ("index_rebalancing_flow", "index_rebalance_day:.9 volume_spike:.6 sector_wide_move:.15"),
  ("options_expiry_effects", "options_expiry_day:.9 volume_spike:.45 volatility_index_jump:.2"),
  ("geopolitical_shock", "volatility_index_jump:.75 correlated_assets_selling_off:.6 currency_move_large:.4 sector_wide_move:.5 credit_spreads_widening:.3"),
  ("sector_rotation", "sector_wide_move:.85 volume_spike:.4 correlated_assets_selling_off:.2"),
  ("credit_contagion", "credit_spreads_widening:.9 correlated_assets_selling_off:.6 volatility_index_jump:.5 bid_ask_spread_widening:.4 circuit_breaker_triggered:.1"),
  ("large_block_trade", "volume_spike:.6 price_gap_at_open:.2 order_book_thin:.35 company_specific_headline:.1"),
  ("rumor_or_leak", "company_specific_headline:.7 price_gap_at_open:.5 volume_spike:.6"),
  ("currency_driven_move", "currency_move_large:.9 sector_wide_move:.4 price_gap_at_open:.3")])

# ───────────────────────── trading systems ─────────────────────────
domain("trading-system-diagnostics", "Trading Systems", "trading system diagnostics", "failure_mode", 0.03,
 "Operational diagnostics for trading systems. Not trading or investment advice.",
 "slippage_above_model fill_rate_low strategy_pnl_drawdown market_data_gap exchange_latency_spike position_limit_breach order_rejects_spike duplicate_orders_sent backtest_live_divergence correlation_regime_change volatility_regime_change stale_quotes risk_alarms_firing clock_sync_drift unexpected_overnight_position",
 [("overfitted_strategy", "backtest_live_divergence:.9 strategy_pnl_drawdown:.6 slippage_above_model:.2"),
  ("market_regime_shift", "volatility_regime_change:.6 correlation_regime_change:.6 strategy_pnl_drawdown:.65 backtest_live_divergence:.35"),
  ("market_data_feed_fault", "market_data_gap:.85 stale_quotes:.7 slippage_above_model:.3 risk_alarms_firing:.25"),
  ("exchange_connectivity_latency", "exchange_latency_spike:.9 slippage_above_model:.6 fill_rate_low:.4 order_rejects_spike:.25"),
  ("execution_model_error", "slippage_above_model:.8 backtest_live_divergence:.45 strategy_pnl_drawdown:.3 fill_rate_low:.3"),
  ("risk_limit_misconfiguration", "position_limit_breach:.75 risk_alarms_firing:.7 order_rejects_spike:.35"),
  ("duplicate_order_bug", "duplicate_orders_sent:.9 position_limit_breach:.5 order_rejects_spike:.3 risk_alarms_firing:.4"),
  ("clock_sync_drift_fault", "clock_sync_drift:.9 stale_quotes:.3 order_rejects_spike:.3 backtest_live_divergence:.2"),
  ("liquidity_deterioration", "fill_rate_low:.7 slippage_above_model:.7 volatility_regime_change:.3 strategy_pnl_drawdown:.3"),
  ("parameter_misconfiguration", "strategy_pnl_drawdown:.45 order_rejects_spike:.35 position_limit_breach:.3 unexpected_overnight_position:.2"),
  ("position_reconciliation_error", "unexpected_overnight_position:.85 position_limit_breach:.35 risk_alarms_firing:.3"),
  ("crowded_trade_unwind", "correlation_regime_change:.55 strategy_pnl_drawdown:.7 volatility_regime_change:.5 fill_rate_low:.3 slippage_above_model:.3"),
  ("fat_finger_input", "order_rejects_spike:.35 position_limit_breach:.5 risk_alarms_firing:.6 slippage_above_model:.35 strategy_pnl_drawdown:.25"),
  ("api_rate_limiting", "order_rejects_spike:.8 fill_rate_low:.4 exchange_latency_spike:.3")])

# ───────────────────────── autonomous driving ─────────────────────────
domain("autonomous-driving-faults", "Autonomous Vehicles", "autonomous vehicle fault diagnosis", "fault_source", 0.03,
 "Illustrative simulator only. Not a safety case, validation result or certification tool.",
 "phantom_braking_events missed_detection_of_object lane_keeping_oscillation localization_drift gnss_dropout camera_glare_or_lens_dirty radar_ghost_targets planner_hesitation hard_stop_at_junction high_inference_latency sensor_time_misalignment map_mismatch disengagement_in_rain_or_fog steering_actuator_lag tracking_id_switches",
 [("camera_lens_contamination", "camera_glare_or_lens_dirty:.9 missed_detection_of_object:.5 disengagement_in_rain_or_fog:.3 phantom_braking_events:.2"),
  ("radar_multipath", "radar_ghost_targets:.85 phantom_braking_events:.6 hard_stop_at_junction:.25"),
  ("gnss_multipath_urban", "gnss_dropout:.7 localization_drift:.7 lane_keeping_oscillation:.3"),
  ("weather_sensor_degradation", "disengagement_in_rain_or_fog:.9 missed_detection_of_object:.5 camera_glare_or_lens_dirty:.3 radar_ghost_targets:.2"),
  ("perception_domain_gap", "missed_detection_of_object:.8 tracking_id_switches:.4 phantom_braking_events:.3"),
  ("sensor_time_sync_fault", "sensor_time_misalignment:.9 tracking_id_switches:.55 localization_drift:.3 lane_keeping_oscillation:.25"),
  ("outdated_map", "map_mismatch:.9 planner_hesitation:.4 localization_drift:.35 hard_stop_at_junction:.3"),
  ("planner_over_conservatism", "planner_hesitation:.85 hard_stop_at_junction:.55 phantom_braking_events:.3"),
  ("steering_actuator_fault", "steering_actuator_lag:.9 lane_keeping_oscillation:.7"),
  ("compute_overload", "high_inference_latency:.9 missed_detection_of_object:.3 planner_hesitation:.3 tracking_id_switches:.25"),
  ("tracking_algorithm_bug", "tracking_id_switches:.85 phantom_braking_events:.3 planner_hesitation:.2"),
  ("extrinsic_calibration_drift", "localization_drift:.45 lane_keeping_oscillation:.45 sensor_time_misalignment:.15 missed_detection_of_object:.25 radar_ghost_targets:.15"),
  ("lidar_partial_failure", "missed_detection_of_object:.6 localization_drift:.4 high_inference_latency:.1"),
  ("map_localization_failure", "localization_drift:.85 map_mismatch:.5 lane_keeping_oscillation:.4 hard_stop_at_junction:.3")])

# ───────────────────────── power grid ─────────────────────────
domain("power-grid-operations", "Power Grid & Utilities", "power grid disturbance diagnosis", "disturbance_cause", 0.03,
 "Illustrative simulator only. Grid operations follow the operator's procedures and protection engineering.",
 "frequency_deviation voltage_sag voltage_swell transformer_temperature_high line_loading_above_limit protection_relay_trip harmonic_distortion reactive_power_shortfall renewable_output_drop load_spike sudden_generation_loss scada_comms_loss ground_fault_indication weather_alert_active",
 [("generator_trip", "sudden_generation_loss:.9 frequency_deviation:.85 protection_relay_trip:.4 voltage_sag:.3"),
  ("transmission_line_fault", "protection_relay_trip:.85 voltage_sag:.7 ground_fault_indication:.4 line_loading_above_limit:.3"),
  ("transformer_overload", "transformer_temperature_high:.9 line_loading_above_limit:.6 load_spike:.35"),
  ("renewable_intermittency", "renewable_output_drop:.9 frequency_deviation:.4 weather_alert_active:.35 voltage_sag:.15"),
  ("demand_surge", "load_spike:.9 line_loading_above_limit:.55 frequency_deviation:.35 voltage_sag:.3 weather_alert_active:.3"),
  ("capacitor_bank_failure", "reactive_power_shortfall:.8 voltage_sag:.6 harmonic_distortion:.3"),
  ("lightning_strike", "weather_alert_active:.75 protection_relay_trip:.7 voltage_swell:.4 ground_fault_indication:.35 scada_comms_loss:.15"),
  ("ground_fault", "ground_fault_indication:.9 protection_relay_trip:.6 voltage_sag:.3"),
  ("nonlinear_load_harmonics", "harmonic_distortion:.9 transformer_temperature_high:.3 voltage_swell:.1"),
  ("scada_comms_failure", "scada_comms_loss:.9 protection_relay_trip:.1"),
  ("cascading_overload", "line_loading_above_limit:.8 protection_relay_trip:.6 frequency_deviation:.5 voltage_sag:.5 sudden_generation_loss:.3"),
  ("protection_misoperation", "protection_relay_trip:.8 voltage_sag:.1"),
  ("vegetation_contact", "protection_relay_trip:.6 ground_fault_indication:.5 weather_alert_active:.4 voltage_sag:.4 line_loading_above_limit:.2")])

# ───────────────────────── agriculture ─────────────────────────
domain("agriculture-crop-health", "Agriculture & Crop Health", "crop health diagnosis", "stress_cause", 0.03,
 "Decision support only. Confirm with a local agronomist or a lab test before treating.",
 "leaf_yellowing leaf_curling wilting_midday leaf_spots stunted_growth uneven_patches_in_field root_discoloration insect_damage_visible white_powdery_coating soil_moisture_low soil_waterlogged recent_heavy_rain recent_frost leaf_tip_burn",
 [("nitrogen_deficiency", "leaf_yellowing:.85 stunted_growth:.5 uneven_patches_in_field:.4"),
  ("drought_stress", "wilting_midday:.85 soil_moisture_low:.9 leaf_curling:.5 leaf_tip_burn:.3 stunted_growth:.3"),
  ("waterlogging_root_rot", "soil_waterlogged:.85 recent_heavy_rain:.6 root_discoloration:.7 wilting_midday:.4 leaf_yellowing:.5 stunted_growth:.4"),
  ("fungal_leaf_spot", "leaf_spots:.9 recent_heavy_rain:.4 leaf_yellowing:.3"),
  ("powdery_mildew", "white_powdery_coating:.9 leaf_curling:.3 stunted_growth:.2"),
  ("aphid_infestation", "insect_damage_visible:.8 leaf_curling:.6 leaf_yellowing:.3 stunted_growth:.2"),
  ("frost_damage", "recent_frost:.9 leaf_tip_burn:.4 wilting_midday:.3 uneven_patches_in_field:.3"),
  ("fertilizer_or_salt_burn", "leaf_tip_burn:.85 wilting_midday:.35 soil_moisture_low:.2 stunted_growth:.25"),
  ("herbicide_drift", "leaf_curling:.7 uneven_patches_in_field:.6 stunted_growth:.4 leaf_yellowing:.3"),
  ("iron_chlorosis", "leaf_yellowing:.75 uneven_patches_in_field:.35 stunted_growth:.25 soil_waterlogged:.2"),
  ("viral_infection", "leaf_yellowing:.5 stunted_growth:.6 leaf_curling:.5 insect_damage_visible:.3 uneven_patches_in_field:.45"),
  ("potassium_deficiency", "leaf_tip_burn:.55 leaf_yellowing:.5 stunted_growth:.3 leaf_spots:.2"),
  ("soil_compaction", "stunted_growth:.6 wilting_midday:.4 uneven_patches_in_field:.6 root_discoloration:.15 soil_waterlogged:.3"),
  ("nematode_damage", "root_discoloration:.5 stunted_growth:.65 uneven_patches_in_field:.6 wilting_midday:.45 leaf_yellowing:.35")])

# ───────────────────────── hospital operations ─────────────────────────
domain("hospital-operations", "Hospital Operations", "hospital operations bottleneck analysis", "bottleneck_cause", 0.03,
 "Operational analytics only. Not clinical decision support.",
 "ed_boarding_hours_rising long_door_to_triage_time high_left_without_being_seen inpatient_beds_full discharges_delayed_afternoon or_turnover_time_up lab_turnaround_slow imaging_backlog nurse_staffing_below_target sick_calls_spike high_overtime_hours surge_in_ed_arrivals respiratory_season_flag ambulance_diversion_active discharge_to_snf_delays room_cleaning_turnaround_slow supply_stockouts",
 [("inpatient_bed_capacity_shortage", "inpatient_beds_full:.9 ed_boarding_hours_rising:.8 high_left_without_being_seen:.45 ambulance_diversion_active:.4"),
  ("discharge_process_delay", "discharges_delayed_afternoon:.85 inpatient_beds_full:.55 ed_boarding_hours_rising:.5"),
  ("nurse_staffing_shortage", "nurse_staffing_below_target:.9 high_overtime_hours:.6 sick_calls_spike:.4 ed_boarding_hours_rising:.3 inpatient_beds_full:.3"),
  ("seasonal_surge", "surge_in_ed_arrivals:.8 respiratory_season_flag:.75 long_door_to_triage_time:.6 high_left_without_being_seen:.5 inpatient_beds_full:.5"),
  ("lab_bottleneck", "lab_turnaround_slow:.9 ed_boarding_hours_rising:.25 long_door_to_triage_time:.15"),
  ("imaging_bottleneck", "imaging_backlog:.9 ed_boarding_hours_rising:.3 discharges_delayed_afternoon:.2"),
  ("or_scheduling_inefficiency", "or_turnover_time_up:.85 inpatient_beds_full:.2"),
  ("post_acute_placement_delay", "discharge_to_snf_delays:.9 inpatient_beds_full:.55 discharges_delayed_afternoon:.4"),
  ("triage_process_inefficiency", "long_door_to_triage_time:.8 high_left_without_being_seen:.6"),
  ("ed_physician_coverage_gap", "high_left_without_being_seen:.5 long_door_to_triage_time:.45 high_overtime_hours:.3"),
  ("room_cleaning_delay", "room_cleaning_turnaround_slow:.9 inpatient_beds_full:.4 ed_boarding_hours_rising:.3"),
  ("supply_shortage", "supply_stockouts:.9 or_turnover_time_up:.35 discharges_delayed_afternoon:.1"),
  ("ambulance_diversion_cascade", "ambulance_diversion_active:.85 surge_in_ed_arrivals:.35 inpatient_beds_full:.5 ed_boarding_hours_rising:.5"),
  ("staff_illness_wave", "sick_calls_spike:.85 nurse_staffing_below_target:.6 high_overtime_hours:.5 respiratory_season_flag:.35")])

CATEGORY = {
 "medical-diagnostics": "Healthcare", "cardiology-ecg-review": "Healthcare", "hospital-operations": "Healthcare",
 "security-incident-investigation": "Technology & Security", "production-incident-rootcause": "Technology & Security",
 "network-infrastructure-outage": "Technology & Security", "ai-ml-system-failures": "Technology & Security",
 "industrial-fault-diagnosis": "Industry & Operations", "manufacturing-quality": "Industry & Operations", "process-plant-operations": "Industry & Operations",
 "supply-chain-disruption": "Industry & Operations", "safety-incident-analysis": "Industry & Operations", "power-grid-operations": "Industry & Operations",
 "agriculture-crop-health": "Industry & Operations",
 "robotics-fault-diagnosis": "Robotics, Mobility & Space", "autonomous-driving-faults": "Robotics, Mobility & Space", "spacecraft-operations": "Robotics, Mobility & Space",
 "financial-fraud-investigation": "Finance & Markets", "financial-markets-analysis": "Finance & Markets", "trading-system-diagnostics": "Finance & Markets",
 "scientific-discovery": "Science & Education", "education-learning-support": "Science & Education",
}
DESCRIPTION = {
 "education-learning-support": "The most likely barrier behind a learner's struggles, from classroom and assessment signals, to help educators choose where to look first.",
 "ai-ml-system-failures": "Why a machine learning or LLM system is underperforming (leakage, drift, retrieval, overfitting and more), from training and production signals.",
 "robotics-fault-diagnosis": "The likely cause of a robot fault or degraded performance, from joint, sensor, power and navigation signals.",
 "process-plant-operations": "The likely cause of a process plant upset (chemical, food, pharma, refining), from temperatures, pressures, flows and instrument signals.",
 "manufacturing-quality": "The root cause of a manufacturing defect or quality drift, from machine, material, operator and measurement signals.",
 "spacecraft-operations": "The likely cause of a spacecraft anomaly, from power, attitude, thermal, communications and fault-protection telemetry.",
 "financial-markets-analysis": "What may explain a market move (earnings, central bank, liquidity, squeeze, flows), from price, volume and event signals. Educational, not advice.",
 "trading-system-diagnostics": "Why a trading system is misbehaving (data, latency, execution, risk, regime), from operational and performance signals. Not advice.",
 "autonomous-driving-faults": "The likely source of an autonomous vehicle fault or odd behaviour, from perception, localization, planning and actuation signals.",
 "power-grid-operations": "The likely cause of a power grid disturbance, from frequency, voltage, protection and weather signals.",
 "agriculture-crop-health": "The likely cause of crop stress, from symptoms in the leaves, roots, soil and recent weather.",
 "hospital-operations": "The operational bottleneck behind ED crowding and delays, from flow, staffing and capacity signals.",
}
# ───────────── batch 2 ─────────────
domain("electric-vehicle-diagnostics", "Electric Vehicles", "electric vehicle fault diagnosis", "fault_cause", 0.03,
 "Illustrative simulator only. Not a substitute for a certified EV technician. High-voltage systems are dangerous.",
 "range_drop_sudden range_drop_cold_weather slow_dc_fast_charging charging_stops_midway reduced_power_limp_mode regen_braking_weak motor_whine_or_vibration inverter_overtemp_warning twelve_volt_battery_drain isolation_fault_warning charge_port_not_latching cabin_heating_draining_range tire_wear_uneven hv_contactor_clicking software_update_recently",
 [("high_voltage_battery_degradation","range_drop_sudden:.55 reduced_power_limp_mode:.4 slow_dc_fast_charging:.45 regen_braking_weak:.3"),
  ("cold_weather_effect","range_drop_cold_weather:.9 slow_dc_fast_charging:.5 regen_braking_weak:.5 cabin_heating_draining_range:.5"),
  ("charger_or_cable_fault","charging_stops_midway:.8 slow_dc_fast_charging:.4 charge_port_not_latching:.2"),
  ("charge_port_latch_failure","charge_port_not_latching:.9 charging_stops_midway:.5"),
  ("inverter_overheating","inverter_overtemp_warning:.9 reduced_power_limp_mode:.6 motor_whine_or_vibration:.3"),
  ("motor_bearing_wear","motor_whine_or_vibration:.9 range_drop_sudden:.2"),
  ("twelve_volt_battery_weak","twelve_volt_battery_drain:.9 hv_contactor_clicking:.4 charging_stops_midway:.2"),
  ("insulation_isolation_fault","isolation_fault_warning:.9 reduced_power_limp_mode:.4 charging_stops_midway:.4"),
  ("hv_contactor_wear","hv_contactor_clicking:.8 reduced_power_limp_mode:.45 charging_stops_midway:.3"),
  ("heat_pump_or_hvac_load","cabin_heating_draining_range:.85 range_drop_cold_weather:.45 range_drop_sudden:.25"),
  ("tire_pressure_or_alignment","tire_wear_uneven:.85 range_drop_sudden:.35 motor_whine_or_vibration:.15"),
  ("regen_calibration_after_update","software_update_recently:.85 regen_braking_weak:.6 range_drop_sudden:.3 reduced_power_limp_mode:.2"),
  ("battery_cell_imbalance","range_drop_sudden:.5 slow_dc_fast_charging:.5 reduced_power_limp_mode:.35 charging_stops_midway:.3")])

domain("ev-battery-system", "EV Battery Systems", "EV battery pack diagnosis", "pack_issue", 0.03,
 "Illustrative simulator only. Battery faults can be a fire or electrical hazard; involve a qualified battery engineer.",
 "cell_voltage_spread_high pack_capacity_fade_fast internal_resistance_rising cell_temperature_gradient_high coolant_flow_low bms_balancing_stuck charge_current_derated self_discharge_high module_temperature_hotspot soc_estimate_jumps voltage_sag_under_load coolant_leak_alarm pack_swelling_or_odor sensor_reading_implausible high_fast_charge_count",
 [("cell_imbalance","cell_voltage_spread_high:.9 bms_balancing_stuck:.4 pack_capacity_fade_fast:.35 charge_current_derated:.3"),
  ("bms_balancing_fault","bms_balancing_stuck:.9 cell_voltage_spread_high:.65 soc_estimate_jumps:.3"),
  ("calendar_aging","pack_capacity_fade_fast:.5 internal_resistance_rising:.5 voltage_sag_under_load:.35"),
  ("fast_charge_wear","high_fast_charge_count:.85 pack_capacity_fade_fast:.6 internal_resistance_rising:.55 cell_temperature_gradient_high:.3"),
  ("coolant_pump_failure","coolant_flow_low:.9 cell_temperature_gradient_high:.6 module_temperature_hotspot:.5 charge_current_derated:.5"),
  ("coolant_leak","coolant_leak_alarm:.9 coolant_flow_low:.55 cell_temperature_gradient_high:.35"),
  ("internal_short_developing","self_discharge_high:.75 module_temperature_hotspot:.5 cell_voltage_spread_high:.5 pack_swelling_or_odor:.3"),
  ("thermal_runaway_precursor","pack_swelling_or_odor:.8 module_temperature_hotspot:.7 cell_temperature_gradient_high:.5 voltage_sag_under_load:.3"),
  ("busbar_connection_resistance","internal_resistance_rising:.5 module_temperature_hotspot:.6 voltage_sag_under_load:.6"),
  ("cell_sensor_fault","sensor_reading_implausible:.9 soc_estimate_jumps:.35 cell_voltage_spread_high:.2"),
  ("soc_estimation_drift","soc_estimate_jumps:.85 pack_capacity_fade_fast:.2"),
  ("lithium_plating","internal_resistance_rising:.5 pack_capacity_fade_fast:.5 high_fast_charge_count:.5 self_discharge_high:.3 voltage_sag_under_load:.3"),
  ("cold_operation_limits","charge_current_derated:.6 voltage_sag_under_load:.45 internal_resistance_rising:.2")])

domain("oil-refinery-operations", "Oil Refinery", "refinery unit upset diagnosis", "upset_cause", 0.03,
 "Illustrative simulator only. Refinery operations follow site procedures and process safety management; involve qualified engineers.",
 "furnace_outlet_temp_low column_pressure_drop_high product_off_spec_sulfur flaring_increase catalyst_activity_falling feed_rate_swing desalter_carryover heat_exchanger_duty_falling pump_seal_leak_alarm compressor_vibration_high crude_slate_changed coke_formation_indicators water_in_product hydrogen_purity_low corrosion_coupon_rate_high",
 [("crude_slate_change","crude_slate_changed:.9 feed_rate_swing:.4 product_off_spec_sulfur:.4 desalter_carryover:.3"),
  ("desalter_upset","desalter_carryover:.9 corrosion_coupon_rate_high:.4 water_in_product:.4 heat_exchanger_duty_falling:.3"),
  ("preheat_exchanger_fouling","heat_exchanger_duty_falling:.9 furnace_outlet_temp_low:.45 column_pressure_drop_high:.3"),
  ("furnace_coking","coke_formation_indicators:.85 furnace_outlet_temp_low:.4 heat_exchanger_duty_falling:.35"),
  ("column_flooding","column_pressure_drop_high:.9 product_off_spec_sulfur:.4 water_in_product:.3 feed_rate_swing:.3"),
  ("catalyst_deactivation","catalyst_activity_falling:.9 product_off_spec_sulfur:.6 hydrogen_purity_low:.35"),
  ("hydrogen_supply_shortfall","hydrogen_purity_low:.85 catalyst_activity_falling:.4 product_off_spec_sulfur:.4"),
  ("compressor_mechanical_issue","compressor_vibration_high:.9 flaring_increase:.4 hydrogen_purity_low:.2"),
  ("pump_seal_failure","pump_seal_leak_alarm:.9 feed_rate_swing:.3 flaring_increase:.2"),
  ("overhead_corrosion","corrosion_coupon_rate_high:.85 water_in_product:.4 pump_seal_leak_alarm:.2"),
  ("flare_gas_recovery_trip","flaring_increase:.85 compressor_vibration_high:.3 feed_rate_swing:.2"),
  ("control_loop_instability","feed_rate_swing:.8 furnace_outlet_temp_low:.25 column_pressure_drop_high:.3 flaring_increase:.2"),
  ("steam_stripping_issue","water_in_product:.7 product_off_spec_sulfur:.3 column_pressure_drop_high:.3")])

domain("gold-refinery-operations", "Gold Refinery", "gold refining process diagnosis", "process_issue", 0.03,
 "Illustrative simulator only. Assay results and refining decisions need qualified metallurgists and certified assays.",
 "fineness_below_target silver_carryover_in_product low_recovery_rate cyanide_concentration_low carbon_loading_slow leach_solution_ph_off slag_viscosity_high furnace_temperature_unstable excess_dross_formation base_metal_contamination electrolyte_contamination cathode_deposit_poor assay_results_inconsistent bullion_weight_mismatch dust_losses_high",
 [("incomplete_chlorination","fineness_below_target:.8 silver_carryover_in_product:.55 base_metal_contamination:.4"),
  ("low_cyanide_strength","cyanide_concentration_low:.9 low_recovery_rate:.6 carbon_loading_slow:.4"),
  ("ph_control_drift","leach_solution_ph_off:.9 low_recovery_rate:.45 cyanide_concentration_low:.3"),
  ("carbon_fouling","carbon_loading_slow:.9 low_recovery_rate:.5 leach_solution_ph_off:.2"),
  ("furnace_temperature_control_fault","furnace_temperature_unstable:.9 slag_viscosity_high:.5 excess_dross_formation:.4 dust_losses_high:.3"),
  ("flux_composition_error","slag_viscosity_high:.8 excess_dross_formation:.5 low_recovery_rate:.3 fineness_below_target:.3"),
  ("silver_separation_failure","silver_carryover_in_product:.9 fineness_below_target:.6"),
  ("feed_base_metal_contamination","base_metal_contamination:.85 fineness_below_target:.5 excess_dross_formation:.4"),
  ("electrolyte_degradation","electrolyte_contamination:.85 cathode_deposit_poor:.7 fineness_below_target:.3"),
  ("dust_extraction_loss","dust_losses_high:.85 bullion_weight_mismatch:.5 low_recovery_rate:.4"),
  ("assay_sampling_error","assay_results_inconsistent:.9 bullion_weight_mismatch:.4 fineness_below_target:.2"),
  ("weighing_or_accounting_error","bullion_weight_mismatch:.8 assay_results_inconsistent:.3"),
  ("current_density_misset","cathode_deposit_poor:.6 electrolyte_contamination:.3 low_recovery_rate:.2")])

domain("sensor-technology-diagnostics", "Sensor Technology", "sensor and measurement fault diagnosis", "sensor_fault", 0.03, None,
 "reading_stuck_constant reading_drifts_slowly noise_level_increased sudden_spikes offset_after_power_cycle temperature_correlated_error saturation_at_limits dropouts_intermittent disagrees_with_redundant_sensor cable_or_connector_wiggle_sensitive supply_voltage_unstable response_time_slower humidity_correlated_error interference_near_motors calibration_overdue",
 [("sensor_element_aging","reading_drifts_slowly:.8 response_time_slower:.5 calibration_overdue:.5 disagrees_with_redundant_sensor:.4"),
  ("stuck_or_failed_sensor","reading_stuck_constant:.9 disagrees_with_redundant_sensor:.7 response_time_slower:.3"),
  ("electrical_noise_emi","noise_level_increased:.8 sudden_spikes:.7 interference_near_motors:.8"),
  ("loose_connector_or_cable","cable_or_connector_wiggle_sensitive:.9 dropouts_intermittent:.7 sudden_spikes:.4"),
  ("thermal_drift","temperature_correlated_error:.9 reading_drifts_slowly:.5 offset_after_power_cycle:.2"),
  ("moisture_ingress","humidity_correlated_error:.85 reading_drifts_slowly:.4 noise_level_increased:.3 dropouts_intermittent:.3"),
  ("power_supply_instability","supply_voltage_unstable:.9 noise_level_increased:.45 dropouts_intermittent:.4 offset_after_power_cycle:.35"),
  ("calibration_error","calibration_overdue:.7 disagrees_with_redundant_sensor:.6 offset_after_power_cycle:.35"),
  ("saturation_or_range_mismatch","saturation_at_limits:.9 sudden_spikes:.2 reading_stuck_constant:.25"),
  ("fouling_or_contamination","response_time_slower:.7 reading_drifts_slowly:.5 noise_level_increased:.2 disagrees_with_redundant_sensor:.4"),
  ("adc_or_amplifier_fault","offset_after_power_cycle:.6 noise_level_increased:.5 saturation_at_limits:.4 reading_stuck_constant:.2"),
  ("sampling_rate_aliasing","noise_level_increased:.5 sudden_spikes:.4 disagrees_with_redundant_sensor:.3"),
  ("mechanical_stress_vibration","interference_near_motors:.3 noise_level_increased:.5 dropouts_intermittent:.3 offset_after_power_cycle:.3 cable_or_connector_wiggle_sensitive:.3")])

domain("renewable-energy-operations", "Renewable Energy", "renewable energy plant diagnosis", "loss_cause", 0.03,
 "Illustrative simulator only. Site maintenance decisions need qualified engineers and OEM guidance.",
 "power_output_below_expected string_current_mismatch inverter_derating hotspots_on_panels soiling_loss_suspected shading_pattern_changed gearbox_vibration_high yaw_misalignment_detected blade_pitch_error generator_temp_high curtailment_active grid_voltage_fluctuation anemometer_disagreement battery_storage_underperforming",
 [("panel_soiling","soiling_loss_suspected:.9 power_output_below_expected:.55 string_current_mismatch:.2"),
  ("partial_shading","shading_pattern_changed:.85 string_current_mismatch:.6 power_output_below_expected:.4"),
  ("panel_cell_degradation","hotspots_on_panels:.8 string_current_mismatch:.5 power_output_below_expected:.45"),
  ("inverter_thermal_derating","inverter_derating:.9 power_output_below_expected:.55 grid_voltage_fluctuation:.2"),
  ("grid_curtailment","curtailment_active:.9 power_output_below_expected:.6 grid_voltage_fluctuation:.4"),
  ("grid_voltage_trips","grid_voltage_fluctuation:.8 inverter_derating:.45 power_output_below_expected:.3"),
  ("gearbox_wear","gearbox_vibration_high:.9 generator_temp_high:.4 power_output_below_expected:.25"),
  ("yaw_misalignment","yaw_misalignment_detected:.9 power_output_below_expected:.5 anemometer_disagreement:.3"),
  ("pitch_system_fault","blade_pitch_error:.9 power_output_below_expected:.45 gearbox_vibration_high:.2"),
  ("anemometer_fault","anemometer_disagreement:.9 yaw_misalignment_detected:.25 power_output_below_expected:.2"),
  ("generator_overheating","generator_temp_high:.9 power_output_below_expected:.35"),
  ("battery_storage_degradation","battery_storage_underperforming:.9 power_output_below_expected:.25"),
  ("low_resource_period","power_output_below_expected:.5 shading_pattern_changed:.1 curtailment_active:.1")])

domain("commodities-trading", "Commodities Trading", "commodity price move analysis", "price_driver", 0.03,
 "Educational analysis of what may explain a commodity move. Not financial advice and not a trading signal.",
 "price_spike inventory_draw_larger_than_expected inventory_build_larger_than_expected supply_disruption_news opec_or_cartel_announcement weather_event_in_producing_region currency_move_large curve_backwardation_deepening curve_contango_widening positioning_extreme_long positioning_extreme_short demand_data_weaker shipping_or_freight_disruption export_restriction_news margin_requirement_change",
 [("supply_disruption","supply_disruption_news:.85 price_spike:.7 curve_backwardation_deepening:.55 inventory_draw_larger_than_expected:.4"),
  ("producer_cartel_decision","opec_or_cartel_announcement:.9 price_spike:.5 curve_backwardation_deepening:.3"),
  ("weather_shock","weather_event_in_producing_region:.9 price_spike:.55 inventory_draw_larger_than_expected:.3"),
  ("inventory_surprise_draw","inventory_draw_larger_than_expected:.9 curve_backwardation_deepening:.5 price_spike:.4"),
  ("inventory_surprise_build","inventory_build_larger_than_expected:.9 curve_contango_widening:.5 demand_data_weaker:.35"),
  ("demand_slowdown","demand_data_weaker:.85 curve_contango_widening:.45 inventory_build_larger_than_expected:.4 positioning_extreme_long:.2"),
  ("dollar_strength_effect","currency_move_large:.85 demand_data_weaker:.2"),
  ("short_covering_rally","positioning_extreme_short:.85 price_spike:.7 curve_backwardation_deepening:.2"),
  ("long_liquidation","positioning_extreme_long:.85 margin_requirement_change:.3 demand_data_weaker:.3"),
  ("shipping_disruption","shipping_or_freight_disruption:.9 curve_backwardation_deepening:.4 price_spike:.4 supply_disruption_news:.3"),
  ("export_ban","export_restriction_news:.9 price_spike:.6 supply_disruption_news:.4"),
  ("margin_driven_selling","margin_requirement_change:.85 positioning_extreme_long:.4 price_spike:.2"),
  ("geopolitical_risk_premium","price_spike:.55 supply_disruption_news:.4 shipping_or_freight_disruption:.3 currency_move_large:.3")])

domain("forex-trading", "Forex Exchange Trading", "currency market move analysis", "fx_driver", 0.03,
 "Educational analysis of what may explain a currency move. Not financial advice and not a trading signal.",
 "sharp_move_vs_peers rate_decision_today inflation_data_surprise employment_data_surprise yield_spread_shift risk_off_flows safe_haven_bid commodity_price_swing intervention_rumor liquidity_thin_session spread_widening political_event_news carry_trade_unwinding month_end_rebalancing option_barrier_nearby",
 [("central_bank_policy_shift","rate_decision_today:.85 yield_spread_shift:.7 sharp_move_vs_peers:.5"),
  ("inflation_surprise","inflation_data_surprise:.9 yield_spread_shift:.55 sharp_move_vs_peers:.4"),
  ("jobs_data_surprise","employment_data_surprise:.9 yield_spread_shift:.45 sharp_move_vs_peers:.35"),
  ("risk_off_episode","risk_off_flows:.9 safe_haven_bid:.7 carry_trade_unwinding:.35 spread_widening:.4"),
  ("carry_trade_unwind","carry_trade_unwinding:.9 risk_off_flows:.4 sharp_move_vs_peers:.5 spread_widening:.3"),
  ("commodity_linked_move","commodity_price_swing:.85 sharp_move_vs_peers:.35"),
  ("official_intervention","intervention_rumor:.8 sharp_move_vs_peers:.6 spread_widening:.4"),
  ("thin_liquidity_move","liquidity_thin_session:.9 spread_widening:.65 sharp_move_vs_peers:.3"),
  ("political_shock","political_event_news:.9 sharp_move_vs_peers:.5 risk_off_flows:.3"),
  ("month_end_flows","month_end_rebalancing:.9 sharp_move_vs_peers:.2"),
  ("option_barrier_effect","option_barrier_nearby:.85 sharp_move_vs_peers:.3 liquidity_thin_session:.15"),
  ("rate_differential_drift","yield_spread_shift:.7 commodity_price_swing:.15 inflation_data_surprise:.2"),
  ("safe_haven_demand","safe_haven_bid:.85 risk_off_flows:.5 political_event_news:.2")])

domain("accounting-system-diagnostics", "Accounting Systems", "accounting discrepancy diagnosis", "discrepancy_cause", 0.03,
 "Operational diagnostics only. Not accounting, tax or legal advice. Material discrepancies need a qualified accountant.",
 "trial_balance_out_of_balance subledger_gl_mismatch bank_rec_unreconciled_items duplicate_invoice_numbers intercompany_balances_dont_match fx_revaluation_differences period_cutoff_entries manual_journal_entries_spike unusual_rounding_differences ar_aging_inconsistent missing_depreciation_run vat_or_tax_mismatch late_posted_transactions integration_error_logged",
 [("duplicate_posting","duplicate_invoice_numbers:.85 subledger_gl_mismatch:.4 bank_rec_unreconciled_items:.4"),
  ("integration_sync_failure","integration_error_logged:.85 subledger_gl_mismatch:.65 late_posted_transactions:.4"),
  ("cutoff_error","period_cutoff_entries:.85 late_posted_transactions:.5 ar_aging_inconsistent:.3"),
  ("unrecorded_bank_items","bank_rec_unreconciled_items:.85 trial_balance_out_of_balance:.2"),
  ("intercompany_timing","intercompany_balances_dont_match:.9 fx_revaluation_differences:.3 period_cutoff_entries:.3"),
  ("fx_revaluation_missing","fx_revaluation_differences:.85 intercompany_balances_dont_match:.4"),
  ("manual_entry_errors","manual_journal_entries_spike:.8 trial_balance_out_of_balance:.5 unusual_rounding_differences:.2"),
  ("rounding_configuration","unusual_rounding_differences:.9 vat_or_tax_mismatch:.35 trial_balance_out_of_balance:.3"),
  ("tax_code_misconfiguration","vat_or_tax_mismatch:.9 subledger_gl_mismatch:.3 unusual_rounding_differences:.25"),
  ("depreciation_run_missed","missing_depreciation_run:.9 period_cutoff_entries:.25"),
  ("unapplied_customer_payments","ar_aging_inconsistent:.85 bank_rec_unreconciled_items:.5"),
  ("one_sided_journal_entry","trial_balance_out_of_balance:.85 manual_journal_entries_spike:.35 integration_error_logged:.2"),
  ("backdated_entries","late_posted_transactions:.6 period_cutoff_entries:.5 manual_journal_entries_spike:.4")])

domain("audit-findings-analysis", "Auditing Systems", "audit finding root-cause analysis", "finding_cause", 0.03,
 "Decision support for audit teams only. Not an audit opinion; professional judgement and evidence are required.",
 "approvals_missing_on_samples segregation_of_duties_conflicts access_rights_not_removed_for_leavers manual_overrides_frequent policy_not_updated_in_years inconsistent_documentation control_performed_late control_evidence_missing high_staff_turnover_in_team recent_system_migration repeat_finding_from_prior_year unusual_journal_entries benfords_law_anomaly vendor_master_data_changes_unreviewed management_pressure_indicators",
 [("control_design_gap","policy_not_updated_in_years:.5 repeat_finding_from_prior_year:.5 approvals_missing_on_samples:.4 inconsistent_documentation:.3"),
  ("control_operating_failure","approvals_missing_on_samples:.8 control_performed_late:.5 control_evidence_missing:.5"),
  ("access_management_weakness","access_rights_not_removed_for_leavers:.85 segregation_of_duties_conflicts:.6 vendor_master_data_changes_unreviewed:.3"),
  ("segregation_of_duties_conflict","segregation_of_duties_conflicts:.9 manual_overrides_frequent:.4 unusual_journal_entries:.3"),
  ("staff_turnover_knowledge_loss","high_staff_turnover_in_team:.85 inconsistent_documentation:.5 control_performed_late:.4"),
  ("system_migration_gaps","recent_system_migration:.85 control_evidence_missing:.5 access_rights_not_removed_for_leavers:.3 inconsistent_documentation:.3"),
  ("management_override","manual_overrides_frequent:.8 unusual_journal_entries:.6 management_pressure_indicators:.6 benfords_law_anomaly:.3"),
  ("potential_fraud_indicators","benfords_law_anomaly:.7 unusual_journal_entries:.6 vendor_master_data_changes_unreviewed:.5 management_pressure_indicators:.4"),
  ("poor_documentation_culture","inconsistent_documentation:.85 control_evidence_missing:.6"),
  ("resource_constraints","control_performed_late:.8 high_staff_turnover_in_team:.4 approvals_missing_on_samples:.3"),
  ("vendor_master_data_weakness","vendor_master_data_changes_unreviewed:.85 segregation_of_duties_conflicts:.3 unusual_journal_entries:.2"),
  ("outdated_policies","policy_not_updated_in_years:.9 repeat_finding_from_prior_year:.4 inconsistent_documentation:.3"),
  ("unremediated_prior_finding","repeat_finding_from_prior_year:.9 control_performed_late:.3 policy_not_updated_in_years:.3")])

CATEGORY.update({"electric-vehicle-diagnostics":"Robotics, Mobility & Space","ev-battery-system":"Robotics, Mobility & Space",
 "oil-refinery-operations":"Energy & Resources","gold-refinery-operations":"Energy & Resources","renewable-energy-operations":"Energy & Resources",
 "sensor-technology-diagnostics":"Technology & Security","commodities-trading":"Finance & Markets","forex-trading":"Finance & Markets",
 "accounting-system-diagnostics":"Finance & Markets","audit-findings-analysis":"Finance & Markets"})
DESCRIPTION.update({
 "electric-vehicle-diagnostics":"The likely cause of an electric vehicle problem (range, charging, power, noises), from driver-visible and diagnostic signals.",
 "ev-battery-system":"What is behind an EV battery pack issue (imbalance, cooling, aging, shorts), from cell, thermal and BMS signals.",
 "oil-refinery-operations":"The likely cause of a refinery unit upset, from furnace, column, catalyst, crude and product-quality signals.",
 "gold-refinery-operations":"The likely cause of a gold refining problem (fineness, recovery, losses), from leach, furnace, electrolysis and assay signals.",
 "sensor-technology-diagnostics":"Why a sensor or measurement chain is misreading (drift, noise, wiring, calibration), from the reading behaviour.",
 "renewable-energy-operations":"Why a solar, wind or storage site is under-producing, from output, inverter, turbine and grid signals.",
 "commodities-trading":"What may explain a commodity price move (supply, inventories, weather, positioning), from market signals. Educational, not advice.",
 "forex-trading":"What may explain a currency move (policy, data, risk flows, liquidity), from market signals. Educational, not advice.",
 "accounting-system-diagnostics":"The likely cause of a ledger or reconciliation discrepancy, from reconciliation, posting and integration signals.",
 "audit-findings-analysis":"The likely root cause of an audit finding, from control-testing and environment signals. Decision support, not an audit opinion.",
})

# ───────────── batch 3 ─────────────
domain("research-development-programs", "Research & Development", "R&D project stall diagnosis", "stall_cause", 0.03,
 "Decision support for R&D leaders. Not a substitute for scientific review.",
 "experiments_not_reproducible milestones_slipping results_contradict_hypothesis long_cycle_between_experiments key_expert_left_team equipment_downtime_frequent budget_overrun_on_materials unclear_success_criteria scope_keeps_expanding data_scattered_across_tools stakeholder_priorities_shifted prototype_fails_in_scale_up literature_review_outdated team_waiting_on_approvals ip_or_regulatory_uncertainty",
 [("irreproducible_methods","experiments_not_reproducible:.9 results_contradict_hypothesis:.4 data_scattered_across_tools:.3"),
  ("wrong_hypothesis","results_contradict_hypothesis:.85 milestones_slipping:.35 literature_review_outdated:.3"),
  ("slow_experiment_cycle","long_cycle_between_experiments:.85 milestones_slipping:.6 equipment_downtime_frequent:.3"),
  ("key_person_dependency","key_expert_left_team:.9 milestones_slipping:.5 experiments_not_reproducible:.3"),
  ("equipment_constraints","equipment_downtime_frequent:.9 long_cycle_between_experiments:.5 milestones_slipping:.45"),
  ("budget_pressure","budget_overrun_on_materials:.85 milestones_slipping:.4 scope_keeps_expanding:.2"),
  ("unclear_goals","unclear_success_criteria:.9 scope_keeps_expanding:.5 stakeholder_priorities_shifted:.4"),
  ("scope_creep","scope_keeps_expanding:.9 milestones_slipping:.55 budget_overrun_on_materials:.35"),
  ("knowledge_fragmentation","data_scattered_across_tools:.85 experiments_not_reproducible:.4 literature_review_outdated:.3"),
  ("strategic_shift","stakeholder_priorities_shifted:.85 unclear_success_criteria:.4 milestones_slipping:.35"),
  ("scale_up_gap","prototype_fails_in_scale_up:.9 milestones_slipping:.4 results_contradict_hypothesis:.25"),
  ("approval_bottleneck","team_waiting_on_approvals:.85 milestones_slipping:.55 long_cycle_between_experiments:.3"),
  ("regulatory_or_ip_block","ip_or_regulatory_uncertainty:.85 team_waiting_on_approvals:.45 stakeholder_priorities_shifted:.3"),
  ("prior_art_blind_spot","literature_review_outdated:.7 results_contradict_hypothesis:.3 ip_or_regulatory_uncertainty:.4 unclear_success_criteria:.15")])

domain("defense-systems-maintenance", "Defense Systems (Readiness)", "defense equipment readiness diagnosis", "readiness_issue", 0.03,
 "Illustrative simulator for equipment readiness, maintenance and logistics only. It does not cover weapons design, targeting or operations.",
 "mission_capable_rate_falling spare_parts_backorders radar_or_sensor_false_alarms comms_link_degraded built_in_test_failures_recurring maintenance_hours_per_flight_hour_rising corrosion_findings_increasing cannibalization_of_parts_rising software_patch_recently_applied power_system_faults technician_shortage_reported depot_turnaround_time_long environmental_exposure_high configuration_mismatch_between_units",
 [("parts_supply_shortfall","spare_parts_backorders:.9 mission_capable_rate_falling:.6 cannibalization_of_parts_rising:.6 depot_turnaround_time_long:.3"),
  ("aging_airframe_or_hull","corrosion_findings_increasing:.6 maintenance_hours_per_flight_hour_rising:.65 mission_capable_rate_falling:.4"),
  ("sensor_calibration_drift","radar_or_sensor_false_alarms:.85 built_in_test_failures_recurring:.5"),
  ("comms_hardware_degradation","comms_link_degraded:.9 built_in_test_failures_recurring:.4 environmental_exposure_high:.2"),
  ("software_regression","software_patch_recently_applied:.85 built_in_test_failures_recurring:.55 radar_or_sensor_false_alarms:.3 configuration_mismatch_between_units:.3"),
  ("power_system_degradation","power_system_faults:.9 built_in_test_failures_recurring:.4 mission_capable_rate_falling:.3"),
  ("maintainer_shortage","technician_shortage_reported:.9 depot_turnaround_time_long:.5 maintenance_hours_per_flight_hour_rising:.3"),
  ("depot_capacity_bottleneck","depot_turnaround_time_long:.85 mission_capable_rate_falling:.45 spare_parts_backorders:.3"),
  ("harsh_environment_wear","environmental_exposure_high:.85 corrosion_findings_increasing:.6 comms_link_degraded:.3"),
  ("configuration_control_gap","configuration_mismatch_between_units:.9 built_in_test_failures_recurring:.4 spare_parts_backorders:.2"),
  ("fault_isolation_weakness","built_in_test_failures_recurring:.6 maintenance_hours_per_flight_hour_rising:.5 radar_or_sensor_false_alarms:.35"),
  ("high_operational_tempo","mission_capable_rate_falling:.6 maintenance_hours_per_flight_hour_rising:.5 power_system_faults:.25 technician_shortage_reported:.3 cannibalization_of_parts_rising:.3"),
  ("training_gap","technician_shortage_reported:.35 maintenance_hours_per_flight_hour_rising:.4 built_in_test_failures_recurring:.3 configuration_mismatch_between_units:.25")])

domain("data-center-operations", "Data Centers", "data center incident diagnosis", "incident_cause", 0.03, None,
 "rack_inlet_temp_high cooling_unit_alarm ups_on_battery pdu_overload_warning power_usage_effectiveness_worsening server_fan_speeds_high intermittent_network_packet_loss storage_latency_spike hot_spots_in_aisle humidity_out_of_range generator_start_failed breaker_tripped fiber_link_flapping monitoring_gaps firmware_update_recent",
 [("crac_or_chiller_failure","cooling_unit_alarm:.9 rack_inlet_temp_high:.7 hot_spots_in_aisle:.5 server_fan_speeds_high:.5 power_usage_effectiveness_worsening:.3"),
  ("airflow_containment_breach","hot_spots_in_aisle:.85 rack_inlet_temp_high:.5 server_fan_speeds_high:.4 power_usage_effectiveness_worsening:.3"),
  ("utility_power_loss","ups_on_battery:.9 generator_start_failed:.2 monitoring_gaps:.2"),
  ("generator_start_failure","generator_start_failed:.85 ups_on_battery:.7"),
  ("circuit_overload","pdu_overload_warning:.85 breaker_tripped:.5"),
  ("ups_battery_degradation","ups_on_battery:.5 breaker_tripped:.2 pdu_overload_warning:.2 monitoring_gaps:.2"),
  ("humidity_control_fault","humidity_out_of_range:.9 cooling_unit_alarm:.3"),
  ("fiber_or_optic_fault","fiber_link_flapping:.85 intermittent_network_packet_loss:.7"),
  ("switch_firmware_bug","firmware_update_recent:.8 intermittent_network_packet_loss:.5 fiber_link_flapping:.25"),
  ("storage_array_issue","storage_latency_spike:.9 monitoring_gaps:.2 firmware_update_recent:.2"),
  ("capacity_overcommit","pdu_overload_warning:.5 power_usage_effectiveness_worsening:.5 server_fan_speeds_high:.4 rack_inlet_temp_high:.35 storage_latency_spike:.3"),
  ("monitoring_blind_spot","monitoring_gaps:.9 hot_spots_in_aisle:.2"),
  ("sensor_miscalibration","power_usage_effectiveness_worsening:.4 humidity_out_of_range:.25 rack_inlet_temp_high:.2 monitoring_gaps:.3")])

domain("software-engineering-delivery", "Software Engineering", "software delivery problem diagnosis", "delivery_issue", 0.03, None,
 "deploy_frequency_dropping lead_time_rising change_failure_rate_high flaky_tests_common long_code_review_wait large_pull_requests merge_conflicts_frequent build_times_long incidents_after_releases tech_debt_complaints onboarding_slow requirements_change_midsprint unclear_ownership_of_services velocity_unstable on_call_burnout_signs",
 [("slow_code_review","long_code_review_wait:.9 lead_time_rising:.6 large_pull_requests:.4 deploy_frequency_dropping:.3"),
  ("oversized_changes","large_pull_requests:.9 merge_conflicts_frequent:.5 change_failure_rate_high:.4 long_code_review_wait:.4"),
  ("weak_test_suite","flaky_tests_common:.85 change_failure_rate_high:.6 incidents_after_releases:.5"),
  ("slow_ci_pipeline","build_times_long:.9 lead_time_rising:.5 deploy_frequency_dropping:.4 flaky_tests_common:.3"),
  ("accumulated_tech_debt","tech_debt_complaints:.85 lead_time_rising:.5 velocity_unstable:.4 change_failure_rate_high:.35"),
  ("unstable_requirements","requirements_change_midsprint:.9 velocity_unstable:.6 merge_conflicts_frequent:.2"),
  ("unclear_ownership","unclear_ownership_of_services:.9 incidents_after_releases:.4 long_code_review_wait:.3 on_call_burnout_signs:.3"),
  ("team_burnout","on_call_burnout_signs:.85 velocity_unstable:.4 incidents_after_releases:.3 onboarding_slow:.2"),
  ("poor_onboarding_docs","onboarding_slow:.9 tech_debt_complaints:.3 lead_time_rising:.2"),
  ("risky_release_process","incidents_after_releases:.8 change_failure_rate_high:.7 deploy_frequency_dropping:.3"),
  ("branching_strategy_problems","merge_conflicts_frequent:.8 lead_time_rising:.4 deploy_frequency_dropping:.3 large_pull_requests:.3"),
  ("understaffing","velocity_unstable:.5 on_call_burnout_signs:.4 long_code_review_wait:.4 deploy_frequency_dropping:.4 onboarding_slow:.2"),
  ("missing_deploy_automation","deploy_frequency_dropping:.7 lead_time_rising:.5 change_failure_rate_high:.4 incidents_after_releases:.3")])

domain("coding-bug-diagnosis", "Coding & Debugging", "code bug diagnosis", "bug_cause", 0.03, None,
 "fails_only_in_production passes_locally_fails_in_ci intermittent_failure nondeterministic_output null_or_undefined_error off_by_one_symptoms memory_grows_over_time cpu_spike_on_certain_inputs fails_after_dependency_upgrade fails_with_concurrent_requests wrong_results_for_edge_inputs timezone_or_locale_sensitive stack_trace_in_third_party_code timeouts_under_load data_corrupted_after_write",
 [("race_condition","fails_with_concurrent_requests:.85 intermittent_failure:.8 nondeterministic_output:.5 data_corrupted_after_write:.3"),
  ("null_handling_bug","null_or_undefined_error:.9 wrong_results_for_edge_inputs:.4 fails_only_in_production:.3"),
  ("off_by_one_error","off_by_one_symptoms:.9 wrong_results_for_edge_inputs:.65"),
  ("memory_leak","memory_grows_over_time:.9 timeouts_under_load:.4 fails_only_in_production:.3"),
  ("algorithmic_complexity","cpu_spike_on_certain_inputs:.85 timeouts_under_load:.6"),
  ("dependency_breaking_change","fails_after_dependency_upgrade:.9 stack_trace_in_third_party_code:.6 passes_locally_fails_in_ci:.3"),
  ("environment_config_difference","fails_only_in_production:.75 passes_locally_fails_in_ci:.7 timezone_or_locale_sensitive:.2"),
  ("timezone_or_locale_bug","timezone_or_locale_sensitive:.9 wrong_results_for_edge_inputs:.4 intermittent_failure:.2"),
  ("unseeded_randomness","nondeterministic_output:.85 intermittent_failure:.55 passes_locally_fails_in_ci:.3"),
  ("transaction_or_write_bug","data_corrupted_after_write:.85 fails_with_concurrent_requests:.3 wrong_results_for_edge_inputs:.25"),
  ("resource_exhaustion","timeouts_under_load:.8 memory_grows_over_time:.35 fails_only_in_production:.4 intermittent_failure:.3"),
  ("third_party_api_change","stack_trace_in_third_party_code:.75 fails_only_in_production:.4 fails_after_dependency_upgrade:.35 null_or_undefined_error:.3"),
  ("input_validation_gap","wrong_results_for_edge_inputs:.8 null_or_undefined_error:.4 cpu_spike_on_certain_inputs:.2 data_corrupted_after_write:.2"),
  ("test_order_dependence","passes_locally_fails_in_ci:.55 intermittent_failure:.5 nondeterministic_output:.4")])

domain("product-development", "Product Development", "product development problem diagnosis", "product_issue", 0.03, None,
 "launch_date_slipping low_beta_adoption high_churn_after_signup feature_usage_low customer_complaints_about_usability requirements_unclear cross_team_dependencies_blocking quality_defects_at_launch cost_per_unit_above_target competitor_launched_similar_product positive_surveys_but_low_sales design_changes_late supplier_lead_times_long testing_findings_late pricing_pushback_in_sales_calls",
 [("poor_product_market_fit","low_beta_adoption:.75 high_churn_after_signup:.6 positive_surveys_but_low_sales:.4 feature_usage_low:.5"),
  ("usability_problems","customer_complaints_about_usability:.9 high_churn_after_signup:.5 feature_usage_low:.5"),
  ("unclear_requirements","requirements_unclear:.9 design_changes_late:.55 launch_date_slipping:.5"),
  ("dependency_bottleneck","cross_team_dependencies_blocking:.9 launch_date_slipping:.65"),
  ("late_testing","testing_findings_late:.85 quality_defects_at_launch:.6 launch_date_slipping:.45 design_changes_late:.3"),
  ("cost_overrun_design","cost_per_unit_above_target:.85 supplier_lead_times_long:.3 pricing_pushback_in_sales_calls:.3"),
  ("supply_chain_delay","supplier_lead_times_long:.85 launch_date_slipping:.55 cost_per_unit_above_target:.3"),
  ("competitive_pressure","competitor_launched_similar_product:.9 low_beta_adoption:.35 pricing_pushback_in_sales_calls:.4"),
  ("pricing_mismatch","pricing_pushback_in_sales_calls:.85 positive_surveys_but_low_sales:.6 competitor_launched_similar_product:.2"),
  ("weak_value_proposition","positive_surveys_but_low_sales:.5 feature_usage_low:.55 low_beta_adoption:.5 pricing_pushback_in_sales_calls:.35"),
  ("quality_process_gap","quality_defects_at_launch:.85 customer_complaints_about_usability:.3 testing_findings_late:.3"),
  ("onboarding_friction","high_churn_after_signup:.8 low_beta_adoption:.3 customer_complaints_about_usability:.4"),
  ("scope_overload","design_changes_late:.6 launch_date_slipping:.55 requirements_unclear:.3 quality_defects_at_launch:.35 cross_team_dependencies_blocking:.3")])

domain("ecommerce-operations", "E-commerce", "e-commerce performance diagnosis", "performance_issue", 0.03, None,
 "conversion_rate_dropped cart_abandonment_up checkout_errors_logged site_speed_slower traffic_up_but_sales_flat paid_traffic_cost_rising mobile_conversion_lagging payment_declines_up stockouts_on_top_products shipping_cost_complaints high_return_rate coupon_code_failures bot_traffic_suspected email_open_rate_down reviews_rating_falling",
 [("checkout_technical_bug","checkout_errors_logged:.9 cart_abandonment_up:.6 conversion_rate_dropped:.6 payment_declines_up:.3"),
  ("slow_site_performance","site_speed_slower:.9 conversion_rate_dropped:.5 mobile_conversion_lagging:.55 cart_abandonment_up:.4"),
  ("traffic_quality_decline","traffic_up_but_sales_flat:.85 paid_traffic_cost_rising:.5 conversion_rate_dropped:.4 bot_traffic_suspected:.3"),
  ("bot_or_scraper_traffic","bot_traffic_suspected:.9 traffic_up_but_sales_flat:.6 site_speed_slower:.4"),
  ("payment_provider_issue","payment_declines_up:.9 checkout_errors_logged:.4 cart_abandonment_up:.4"),
  ("stockout_problem","stockouts_on_top_products:.9 conversion_rate_dropped:.4 traffic_up_but_sales_flat:.3"),
  ("shipping_cost_friction","shipping_cost_complaints:.85 cart_abandonment_up:.65"),
  ("mobile_experience_issue","mobile_conversion_lagging:.85 site_speed_slower:.3 cart_abandonment_up:.3"),
  ("product_quality_problem","high_return_rate:.8 reviews_rating_falling:.7 conversion_rate_dropped:.3"),
  ("promo_configuration_error","coupon_code_failures:.9 checkout_errors_logged:.35 cart_abandonment_up:.4"),
  ("ad_channel_saturation","paid_traffic_cost_rising:.85 traffic_up_but_sales_flat:.4"),
  ("email_deliverability_decline","email_open_rate_down:.85 traffic_up_but_sales_flat:.2"),
  ("pricing_uncompetitive","conversion_rate_dropped:.5 cart_abandonment_up:.45 shipping_cost_complaints:.3 reviews_rating_falling:.15 traffic_up_but_sales_flat:.4")])

domain("retail-store-operations", "Retail", "retail performance diagnosis", "performance_driver", 0.03, None,
 "sales_below_forecast foot_traffic_down conversion_rate_in_store_down average_basket_size_down stockouts_on_shelf overstock_markdowns_rising shrinkage_rising long_checkout_queues staff_turnover_high promotions_underperforming competitor_opened_nearby negative_store_reviews planogram_not_followed seasonal_pattern_shift price_gap_vs_competitors",
 [("store_traffic_decline","foot_traffic_down:.9 sales_below_forecast:.6 competitor_opened_nearby:.3"),
  ("new_local_competitor","competitor_opened_nearby:.9 foot_traffic_down:.6 sales_below_forecast:.4 price_gap_vs_competitors:.3"),
  ("on_shelf_availability_gap","stockouts_on_shelf:.9 sales_below_forecast:.5 conversion_rate_in_store_down:.4 negative_store_reviews:.3"),
  ("poor_demand_forecasting","overstock_markdowns_rising:.8 stockouts_on_shelf:.5 sales_below_forecast:.4"),
  ("theft_or_process_loss","shrinkage_rising:.9 overstock_markdowns_rising:.1"),
  ("understaffed_checkout","long_checkout_queues:.9 negative_store_reviews:.5 conversion_rate_in_store_down:.35"),
  ("staff_turnover_effect","staff_turnover_high:.85 negative_store_reviews:.4 planogram_not_followed:.4 conversion_rate_in_store_down:.3"),
  ("ineffective_promotions","promotions_underperforming:.85 average_basket_size_down:.4 sales_below_forecast:.4"),
  ("merchandising_execution_gap","planogram_not_followed:.85 conversion_rate_in_store_down:.45 average_basket_size_down:.3"),
  ("seasonal_shift","seasonal_pattern_shift:.85 sales_below_forecast:.55 overstock_markdowns_rising:.4 foot_traffic_down:.3"),
  ("price_competitiveness_gap","price_gap_vs_competitors:.85 conversion_rate_in_store_down:.4 average_basket_size_down:.4"),
  ("weak_customer_experience","negative_store_reviews:.8 conversion_rate_in_store_down:.55 long_checkout_queues:.3 staff_turnover_high:.3"),
  ("shrinking_consumer_spend","average_basket_size_down:.8 sales_below_forecast:.5 promotions_underperforming:.3 foot_traffic_down:.3")])

CATEGORY.update({"research-development-programs":"Science & Education","defense-systems-maintenance":"Industry & Operations",
 "data-center-operations":"Technology & Security","software-engineering-delivery":"Technology & Security","coding-bug-diagnosis":"Technology & Security",
 "product-development":"Industry & Operations","ecommerce-operations":"Commerce & Retail","retail-store-operations":"Commerce & Retail"})
DESCRIPTION.update({
 "research-development-programs":"Why an R&D programme is stalling or slipping, from experiment, team, budget and approval signals.",
 "defense-systems-maintenance":"Why defence equipment readiness is falling (parts, maintenance, configuration, environment). Readiness and logistics only, not weapons or operations.",
 "data-center-operations":"The likely cause of a data centre incident, from cooling, power, network and storage signals.",
 "software-engineering-delivery":"Why software delivery is slow or unreliable, from review, CI, release and team signals.",
 "coding-bug-diagnosis":"The likely cause of a software bug, from how and when it fails.",
 "product-development":"What is holding back a product (launch delay, adoption, churn, cost), from development and market signals.",
 "ecommerce-operations":"Why an online store's sales or conversion are off, from funnel, site, payment and traffic signals.",
 "retail-store-operations":"Why a store or chain is underperforming, from traffic, stock, staffing and promotion signals.",
})

for _d in D:
    _d["category"] = CATEGORY[_d["slug"]]
    if _d["slug"] in DESCRIPTION: _d["description"] = DESCRIPTION[_d["slug"]]


# ── Validation status ────────────────────────────────────────────────────────
# Every domain starts as "illustrative" (hand-set probabilities). A domain is "calibrated" only when
# calibrations/<slug>.json exists, written by calibrate.py from real labelled cases and a held-out check.
# "expert_validated" is never set by a tool: it needs a named domain expert's sign-off recorded in
# calibrations/<slug>.json under validation.signed_off_by.
STATUSES = ("illustrative", "calibrated", "expert_validated")
_cal_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "calibrations")
for _d in D:
    _d["validation"] = {"status": "illustrative"}
    _f = os.path.join(_cal_dir, _d["slug"] + ".json")
    if os.path.exists(_f):
        _c = json.load(open(_f))
        _d["profiles"] = {c: {s: float(p) for s, p in _c["profiles"][c].items()} for c in _d["causes"]}
        _d["validation"] = _c["validation"]


def validate(domains):
    slugs = set()
    for d in domains:
        assert d.get("category"), (d["slug"], "missing category")
        assert d["validation"]["status"] in STATUSES, (d["slug"], d["validation"])
        if d["validation"]["status"] == "expert_validated": assert d["validation"].get("signed_off_by"), (d["slug"], "expert_validated needs signed_off_by")
        assert d["slug"] not in slugs; slugs.add(d["slug"])
        assert 12 <= len(d["causes"]) <= 15, (d["slug"], len(d["causes"]))
        assert len(set(d["causes"])) == len(d["causes"]) and len(set(d["signals"])) == len(d["signals"])
        used = set()
        for c, prof in d["profiles"].items():
            for s, p in prof.items():
                assert s in d["signals"], (d["slug"], c, s)
                assert 0 < p < 1, (d["slug"], c, s, p); used.add(s)
        assert used == set(d["signals"]), (d["slug"], "unused signals", set(d["signals"]) - used)

if __name__ == "__main__":
    validate(D)
    here = os.path.dirname(os.path.abspath(__file__))
    targets = [os.path.join(here, "domains_spec.json"), os.path.join(here, "..", "..", "backend", "simulators", "domains_spec.json")]
    text = json.dumps({"version": 4, "domains": D}, indent=1) + "\n"
    for t in targets:
        open(t, "w").write(text)
    print(f"wrote {len(D)} domains, {sum(len(d['causes']) for d in D)} causes to {len(targets)} files")
