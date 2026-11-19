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


def validate(domains):
    slugs = set()
    for d in domains:
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
    text = json.dumps({"version": 2, "domains": D}, indent=1) + "\n"
    for t in targets:
        open(t, "w").write(text)
    print(f"wrote {len(D)} domains, {sum(len(d['causes']) for d in D)} causes to {len(targets)} files")
