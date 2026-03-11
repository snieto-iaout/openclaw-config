# HubSpot field mapping (template)

Completa estos nombres de propiedades según tu portal HubSpot.

## Company properties

- name -> `name`
- domain -> `domain`
- industry/sector (Real Estate|Security|Construction) -> `industry` (o custom: `sector__c`)
- tipo ("Cliente potencial") -> `type` (o custom)
- city -> `city`
- state/region -> `state`
- country -> `country`
- zip -> `zip`
- numberofemployees (estimado) -> `numberofemployees`
- annualrevenue (estimado) -> `annualrevenue`
- timezone -> (custom) `time_zone`
- description -> `description`
- linkedin_company_page -> (custom) `linkedin_company_page`
- owner/team routing -> `hubspot_owner_id` OR custom `owner_team`
- lead_score -> (custom) `lead_score`
- icp_segment -> (custom) `icp_segment`
- lead_source -> `hs_lead_status` / `hs_analytics_source` / custom

## Contact properties

- firstname -> `firstname`
- lastname -> `lastname`
- jobtitle -> `jobtitle`
- email -> `email`
- linkedin_profile_url -> (custom) `linkedin_profile_url`

## Associations

- Contact -> Company association type: default.

## Notes

- Use Engagements/Notes API (CRM v3 Objects: notes) and associate to company and contact when available.

