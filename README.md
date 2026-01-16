### **Description**

This repository orchestrates the workflow for processing community energy models. It retrieves archetype `.h2k` models from a dedicated archetypes repository and updates the weather reference to match the specific community. The updated models are then passed to a converter repository (which remains unchanged) to produce EnergyPlus-ready outputs and hourly energy usage data.

Changing the weather reference drives downstream model behavior because heating and cooling loads depend on climate. As a result, the same archetype produces different hourly loads in different communities even when envelope and internal gains remain constant.


### **Approach**

**This repository:** Retrieve archetype `.h2k` models, update their weather reference to match the target community, then pass the modified models to the converter.

**Converter repository:** Convert the weather-updated `.h2k` files to HPXML format and run EnergyPlus simulations to produce hourly energy usage data.

**This repository (post-conversion):** Collect and organize converter outputs into the desired structure for downstream use.

⦁   Treat "community" as a weather selection: if the input `.h2k` already encodes the intended Region/Location, keep it; otherwise, apply the repository's convention to set the weather reference.


### **Testing Plan**

⦁	Run the CLI on a small directory of `.h2k` files with different Region/Location values; confirm HPXML is produced and EnergyPlus artifacts (e.g., `eplusout.sql`) appear when simulation is enabled.

⦁	Verify that summary artifacts (e.g., run summaries and database) reflect success/failure per case, aligned with current tests.


### **Waiting On**

⦁	Orchestrator contract: whether it will call the CLI or API and any batch metadata it expects us to return.
