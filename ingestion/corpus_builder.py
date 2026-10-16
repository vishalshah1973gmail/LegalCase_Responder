"""Synthetic property-law corpus generator.

Every case produced here is CLEARLY FICTIONAL by construction:

* Jurisdictions are invented U.S.-style states that do not exist (Westmarch,
  Calloway, Northridge, ...), so no real court is imitated.
* Docket numbers use a reserved ``SYN-`` prefix and could not collide with a
  real docket.
* Party and firm names are drawn from invented name pools.
* Every record carries ``source: "synthetic"`` and a ``fictional_notice`` field.

The generator is deterministic for a given seed, so the corpus can be rebuilt
byte-for-byte without re-fetching anything.
"""
from __future__ import annotations

import json
import random
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List

FICTIONAL_NOTICE = (
    "FICTIONAL DOCUMENT. Generated for the LegalCase Responder demo corpus. The "
    "parties, court, docket number and holdings below are invented and do not "
    "correspond to any real case, court, or person."
)

# --------------------------------------------------------------- name pools
STATES = [
    ("Westmarch", "WM"), ("Calloway", "CW"), ("Northridge", "NR"),
    ("Sable", "SB"), ("Ardenne", "AR"), ("Kestrel", "KS"),
    ("Fairhollow", "FH"), ("Brightwater", "BW"), ("Thornfield", "TF"),
    ("Marrowdale", "MD"),
]
COURT_FORMS = [
    "Court of Appeals of {state}",
    "Supreme Court of {state}",
    "{state} Superior Court, {county} County",
    "{state} District Court of Appeal, {n} District",
    "{state} Land and Property Court, {county} Division",
]
COUNTIES = [
    "Ashbourne", "Lindenmere", "Grayrock", "Harrowgate", "Pinecrest",
    "Elmsworth", "Rooksbury", "Windmere", "Cobbleton", "Stillwater",
]
SURNAMES = [
    "Alderidge", "Brackenbury", "Cadwallon", "Dunmoor", "Ellsworth-Vane",
    "Fenwicke", "Grimsby-Hale", "Havershaw", "Ingleside", "Jarrowmere",
    "Kettleburn", "Lowbridge", "Marchetti-Doyle", "Nettleford", "Oakhampton",
    "Prendergast", "Quillon", "Ravensmere", "Stroudwick", "Thackeray-Bell",
    "Umberton", "Vosswood", "Wraymond", "Yarborough", "Zellwood",
]
FIRST_NAMES = [
    "Adaline", "Bertram", "Cordelia", "Desmond", "Evanthe", "Fitzwilliam",
    "Georgiana", "Horatio", "Isolde", "Jasper", "Katarin", "Lucian",
    "Marisol", "Nikolai", "Ottoline", "Perrin", "Rosalind", "Silas",
    "Theodora", "Ulric", "Verity", "Wendell",
]
ENTITY_FORMS = [
    "{n} Holdings, LLC", "{n} Property Group, Inc.", "{n} Realty Trust",
    "{n} Development Partners, L.P.", "{n} Homeowners Association, Inc.",
    "{n} Capital Servicing, LLC", "{n} Land & Timber Co.",
    "{n} Municipal Housing Authority",
]
ENTITY_ROOTS = [
    "Marbury Hollow", "Cinderfield", "Two Rivers", "Blackthorn Ridge",
    "Applegate Commons", "Halloway Bend", "Stonebrook", "Verdant Acre",
    "Kingsmere", "Quarrytown", "Larkspur Hill", "Foxglove Landing",
    "Amberline", "Deepwell", "Saltmarsh", "Copperfield Row",
]
STREETS = [
    "Wicklow Lane", "Ferndale Road", "Mill Race Way", "Old Quarry Turnpike",
    "Harper's Cut", "Bellweather Street", "Sycamore Reach", "Kingfisher Drive",
    "Pennyroyal Court", "Tanner's Row",
]

CASE_TYPES = [
    "landlord_tenant", "easement", "boundary_title", "hoa_covenant",
    "foreclosure", "adverse_possession", "zoning", "lease_rider",
    "eminent_domain", "water_rights",
]

CASE_TYPE_LABELS = {
    "landlord_tenant": "Landlord-Tenant",
    "easement": "Easement",
    "boundary_title": "Boundary / Title",
    "hoa_covenant": "HOA / Restrictive Covenant",
    "foreclosure": "Foreclosure",
    "adverse_possession": "Adverse Possession",
    "zoning": "Zoning / Land Use",
    "lease_rider": "Lease Rider / Addendum",
    "eminent_domain": "Eminent Domain",
    "water_rights": "Water & Mineral Rights",
}


# --------------------------------------------------------------- text banks
# Each case type has a bank of paragraph, rider and clause templates. Templates
# use ``{}``-style slots filled from the fictional name pools above.

PARAGRAPHS: Dict[str, List[str]] = {
"landlord_tenant": [
 "Appellant {plaintiff} is the record owner of the residential building located at {property}, a {units}-unit structure operated as rental housing since {year0}. Appellee {defendant} occupied Unit {unit} under a written lease dated {leasedate}.",
 "The lease provided for monthly rent of ${rent}, due on the first day of each month, with a late charge of ${late} assessed on any installment remaining unpaid after the {days}th day of the month. The trial court found that this charge operated as a penalty rather than as liquidated damages.",
 "A late fee is enforceable only where it bears a reasonable relationship to the administrative cost actually incurred by the landlord in processing a delinquent payment. A charge of ${late} against a monthly obligation of ${rent} exceeds that relationship and is unenforceable to the extent it exceeds five percent of the installment.",
 "{defendant} withheld rent for the months of {month1} and {month2} of {year1}, asserting that the premises were untenantable by reason of a persistent failure of the heating system and recurring water intrusion at the north wall of the unit.",
 "The implied warranty of habitability is not waivable by lease term. Any provision purporting to require a tenant to accept the premises 'as is' is void as against the public policy of this State insofar as it reaches conditions materially affecting health and safety.",
 "The record establishes that {plaintiff} received written notice of the heating defect on {noticedate} and did not dispatch a repair contractor until {repairdate}, an interval of {days2} days. During that interval overnight interior temperatures fell below fifty-five degrees on at least eleven occasions.",
 "A tenant electing to withhold rent under the repair-and-deduct statute must (1) give written notice of the defect, (2) allow a reasonable time for cure, and (3) deposit the withheld sums with the clerk of court or into a segregated account. {defendant} satisfied the first two requirements but did not deposit the withheld rent.",
 "The security deposit of ${deposit} was not returned within {days3} days of surrender, nor was an itemized statement of deductions furnished. The statutory consequence is forfeiture of the landlord's right to retain any portion of the deposit.",
 "{plaintiff} served a notice to quit on {noticedate2}. The notice recited the ground of non-payment but omitted the amount claimed to be due. A notice to quit that fails to state the sum demanded does not commence the statutory cure period.",
 "Retaliatory eviction is presumed where a landlord commences a summary possession action within {months} months after a tenant has reported a code violation to the municipal housing inspector. The presumption is rebuttable by clear and convincing evidence of an independent, non-retaliatory ground.",
 "The trial court awarded {defendant} attorney's fees of ${fees} under the reciprocal-fee provision. Where a lease grants fees to the landlord, this State reads the provision as mutual, and the prevailing tenant recovers on the same terms.",
 "We affirm in part and reverse in part. The judgment of possession is vacated; the money judgment is remanded for recalculation consistent with the late-fee holding set out above.",
],
"easement": [
 "This appeal concerns a claimed easement of access across the northern {feet} feet of the parcel at {property}, owned by {defendant}, in favor of the landlocked rear parcel owned by {plaintiff}.",
 "An easement by necessity arises where (1) the dominant and servient estates were formerly held in common ownership, (2) that unity was severed, and (3) the necessity for the way existed at the moment of severance. Necessity arising afterward will not support the easement.",
 "The common grantor conveyed the rear parcel in {year0} without any reservation of a right of way. At that time the rear parcel abutted {oldroad}, which was subsequently vacated by the {county} County Board, leaving the parcel without lawful access.",
 "Because the want of access arose from the later vacation of a public road rather than from the severance itself, no easement by necessity was created. The trial court's contrary conclusion was error.",
 "An easement by prescription requires use that is open, notorious, continuous, hostile and under a claim of right for the full statutory period of {years} years. Permissive use, however long continued, never ripens into a prescriptive right.",
 "The evidence showed that {plaintiff} and predecessors drove a gravel track across the servient estate from {year0} through {year1}, maintained it with periodic grading, and installed a culvert at the drainage swale in {year2}.",
 "Acts of maintenance visible to the servient owner are strong evidence that the use was under a claim of right rather than by neighborly accommodation. The grading and culvert installation here satisfy that standard.",
 "The scope of an easement is fixed by the use that created it. A prescriptive way established by passenger vehicles and light farm equipment does not expand to accommodate commercial haul traffic of the character now proposed by {plaintiff}.",
 "The servient owner retains the right to make any use of the burdened land that does not unreasonably interfere with the easement. Installation of a gate is permissible provided it is not locked against the dominant owner.",
 "An easement appurtenant runs with the land and passes on conveyance of the dominant estate whether or not it is mentioned in the deed. It is extinguished only by release, merger, abandonment, or prescription running against it.",
 "Abandonment requires more than mere non-use. There must be an affirmative act evincing an intent to relinquish the right permanently. The fifteen years of non-use shown here, standing alone, does not extinguish the easement.",
 "The judgment declaring a prescriptive easement is affirmed as to the way as historically used, and modified to exclude the proposed commercial expansion. Costs to {defendant}.",
],
"boundary_title": [
 "The parties own adjoining parcels on {street}. The dispute concerns a strip approximately {feet} feet in width lying between the fence line maintained since {year0} and the line described in the parties' respective deeds.",
 "Where a deed description conflicts with monuments actually set on the ground, the monuments control. Calls in a conveyance are given priority in the order: natural monuments, artificial monuments, courses, distances, and quantity.",
 "The surveyor called by {plaintiff} located the original iron pin at the southeast corner and retraced the line from that monument. The surveyor called by {defendant} began from a subdivision plat computation without locating any original monument.",
 "A retracement that ignores an original monument capable of being located is entitled to little weight. We accept the trial court's finding crediting the monument-based survey.",
 "The doctrine of acquiescence establishes a boundary where adjoining owners have recognized and treated a visible line as the boundary for the statutory period, regardless of what the deeds provide.",
 "Acquiescence requires (1) occupation up to a visible line, (2) mutual recognition of that line as the boundary, and (3) continuance for {years} years. Silence coupled with occupation may supply the element of mutual recognition.",
 "The fence erected in {year0} was maintained jointly, and both households mowed to their respective sides without objection until {plaintiff} obtained the {year1} survey. That course of conduct satisfies the acquiescence standard.",
 "A quiet-title plaintiff must recover on the strength of its own title and not on the weakness of the defendant's. {plaintiff} traced an unbroken chain to the {year2} patent and thereby carried that burden as to the residue of the parcel.",
 "The recording act of this State is a race-notice statute. A subsequent purchaser for value prevails over a prior unrecorded interest only if the purchaser took without notice and recorded first.",
 "{defendant} had constructive notice of the disputed occupation. Possession that is open and visible puts a purchaser on inquiry as to the rights of the possessor, and a purchaser who fails to inquire is charged with what inquiry would have disclosed.",
 "The trial court's reformation of the deed to correct a scrivener's transposition of the bearing from N {bear1} E to N {bear2} E is supported by clear and convincing evidence of mutual mistake.",
 "The judgment quieting title in {plaintiff} to the disputed strip is affirmed. The counterclaim for trespass damages is remanded for a determination of the value of the removed timber.",
],
"hoa_covenant": [
 "{plaintiff}, the association governing the {subdiv} subdivision, brought this action to enjoin {defendant} from maintaining a detached structure at {property} in violation of Article {art} of the recorded declaration.",
 "Restrictive covenants are enforceable servitudes running with the land where they are (1) in writing, (2) intended to run, (3) touching and concerning the land, and (4) recorded so as to give notice to successors.",
 "Covenants are construed in favor of the free use of land. Ambiguity in a restriction is resolved against the party seeking to enforce it, and a restriction will not be extended by implication to conduct not fairly within its terms.",
 "Article {art} prohibits 'any outbuilding, shed or accessory structure exceeding one hundred twenty square feet.' The structure erected by {defendant} measures {sqft} square feet and is therefore within the plain reach of the restriction.",
 "The association's architectural review committee denied the application by letter dated {noticedate}. The declaration requires that denials state the specific ground relied upon; the letter recited only that the proposal was 'not in harmony with the community.'",
 "A discretionary architectural approval power must be exercised reasonably and in good faith. A denial that states no articulable standard is arbitrary and will not support injunctive relief.",
 "The defense of changed conditions requires a showing that the character of the neighborhood has so altered that the original purpose of the restriction can no longer be achieved. Isolated violations elsewhere in the subdivision do not meet that standard.",
 "The association waived enforcement as to fence height by failing to act against {n_viol} comparable violations over a period of {years} years. Selective enforcement of a covenant against one owner, after acquiescence in like violations by others, is inequitable.",
 "Assessments levied under Article {art2} became a lien on the lot upon recording of the notice of assessment. The lien is subordinate to a first mortgage recorded earlier in time but superior to subsequent encumbrances.",
 "The business judgment rule shields the board's maintenance and budgeting decisions from judicial second-guessing where the board acted within its authority, on an informed basis, and in the honest belief that the action served the association.",
 "Fines totaling ${fines} were imposed without the hearing required by the bylaws. A fine imposed in disregard of the association's own procedural requirements is void, without regard to the merits of the underlying violation.",
 "We reverse the injunction as to the fence and affirm as to the accessory structure. The award of fines is vacated in its entirety.",
],
"foreclosure": [
 "{plaintiff}, as servicer for the holder of the note, commenced this foreclosure against {defendant} with respect to the property at {property}, securing an original principal balance of ${principal}.",
 "Standing to foreclose requires that the plaintiff hold the note, endorsed in blank or to the plaintiff, at the time the complaint is filed. A later-acquired endorsement does not cure a standing defect existing at filing.",
 "The allonge produced at trial was undated and was not physically affixed to the note when the original was tendered for inspection. An allonge must be affixed to the instrument to be effective as an endorsement.",
 "The mortgage requires that a notice of default be sent to the borrower's last known address, specifying the default, the action required to cure, a date not less than {days} days from the notice by which the default must be cured, and the borrower's right to reinstate.",
 "Strict compliance with contractual notice conditions is a condition precedent to acceleration. The notice sent to {defendant} omitted the reinstatement advisory and was therefore ineffective to accelerate the debt.",
 "{defendant} made {npay} payments under a trial loan-modification plan and was thereafter denied a permanent modification on the ground of an unverified escrow shortfall of ${escrow}.",
 "A servicer that accepts payments under a trial plan and then denies permanent modification without the review the plan promises may be estopped from asserting the default those payments were tendered to cure.",
 "The statute of limitations on a foreclosure action runs from acceleration, not from the original maturity date. Where an earlier acceleration was withdrawn by dismissal of a prior action, the limitations clock is reset as to installments coming due thereafter.",
 "A deficiency judgment is available only where the foreclosure sale price is confirmed as commercially reasonable. The bid of ${bid} against an appraised value of ${appraised} is presumptively unreasonable and requires an evidentiary hearing.",
 "The equity of redemption may be exercised at any time before the sale is confirmed. Tender must be of the full accelerated balance plus costs, not merely of the arrearage, once acceleration has validly occurred.",
 "Post-sale, the purchaser takes subject to any bona fide tenancy of record. A tenant in possession under a lease predating the mortgage is not divested by the sale.",
 "The judgment of foreclosure is vacated and the cause remanded with directions to dismiss without prejudice for failure to satisfy the notice condition precedent.",
],
"adverse_possession": [
 "{plaintiff} claims title by adverse possession to a {acres}-acre wooded tract adjoining {property}, of which {defendant} is the record owner.",
 "Adverse possession requires possession that is actual, open and notorious, exclusive, hostile, and continuous for the statutory period of {years} years. Each element must be established by clear and convincing evidence.",
 "Possession is 'actual' where the claimant uses the land as an ordinary owner of similar land would use it. For wooded acreage, selective timbering, posting, and seasonal recreational use may suffice where cultivation would not be expected.",
 "{plaintiff} posted the tract against trespass in {year0}, cut and sold standing timber in {year1} and {year2}, and maintained a hunting camp on the northeast quarter continuously thereafter.",
 "Hostility does not require ill will. It requires only that the possession be without the record owner's permission and inconsistent with the owner's title. A claimant's mistaken belief as to the true line does not defeat hostility in this State.",
 "Payment of property taxes is not an independent element in this jurisdiction but is evidence bearing on the notoriety of the claim. {plaintiff} paid taxes assessed against the tract for {ntax} of the {years} years in question.",
 "Tacking is permitted between successive possessors in privity. {plaintiff} may tack the {years2} years of possession by its predecessor, whose deed purported to convey the disputed tract, to satisfy the statutory term.",
 "Continuity is broken by an entry of the record owner made with intent to reclaim possession. The single survey visit by {defendant}'s agent in {year3}, unaccompanied by any assertion of possession, did not interrupt the running of the statute.",
 "Color of title is not required where the claim rests on actual occupancy, but it enlarges the claim to the full extent of the described premises rather than the portion actually occupied.",
 "Land held by a municipality for a public purpose is not subject to adverse possession. The {feet}-foot strip within the platted right of way is therefore excluded from any judgment in {plaintiff}'s favor.",
 "The trial court found the elements satisfied as to {acres2} acres and not satisfied as to the remainder, which lay beyond any fence or posted line. That allocation is not clearly erroneous.",
 "Affirmed in part, reversed in part, and remanded for entry of a decree describing the vested tract by metes and bounds consistent with the surveyor's Exhibit {ex}.",
],
"zoning": [
 "{plaintiff} appeals the denial by the {county} County Board of Adjustment of a use variance permitting operation of a {usetype} at {property}, a parcel zoned R-{zone} single-family residential.",
 "A use variance requires proof of unnecessary hardship: that the property cannot yield a reasonable return in any permitted use, that the hardship is unique to the parcel, and that the variance will not alter the essential character of the locality.",
 "Hardship must arise from the land itself and not from the owner's personal circumstances or from a self-created condition. Purchase with knowledge of the restriction is a factor but is not, standing alone, disqualifying.",
 "The parcel is {sqft} square feet, irregular in shape, and burdened by a drainage easement across {pct} percent of its buildable area. Those are conditions of the land and not of the owner.",
 "An area variance is governed by a balancing test weighing the benefit to the applicant against the detriment to the health, safety and welfare of the neighborhood, and does not require the showing of hardship applicable to use variances.",
 "A nonconforming use lawfully existing at the effective date of the ordinance may continue but may not be enlarged, and is lost by abandonment or by discontinuance for the period specified in the ordinance.",
 "Discontinuance for {months} months is presumed abandonment under Section {sec} of the ordinance. The presumption is rebutted by proof of an intent to resume coupled with overt acts consistent with that intent.",
 "Spot zoning is the singling out of a small parcel for treatment differing from that of surrounding property, for the benefit of the owner and to the detriment of the comprehensive plan. The rezoning here served a plan objective and is not spot zoning.",
 "The board's findings must be sufficient to permit meaningful review. Conclusory recitals tracking the language of the ordinance, without reference to record evidence, require remand.",
 "Vested rights against a subsequent ordinance arise where the developer, in good-faith reliance on a validly issued permit, has made substantial expenditures. {plaintiff} expended ${spend} on site work before the moratorium was adopted.",
 "Exhaustion of administrative remedies is a prerequisite to judicial review. A facial constitutional challenge to the ordinance is excepted from that requirement.",
 "The denial is vacated and the matter remanded to the Board for findings addressing the drainage easement and the shape of the parcel.",
],
"lease_rider": [
 "This action turns on the construction of three riders appended to a commercial lease between {plaintiff}, as landlord, and {defendant}, as tenant, for {sqft} square feet at {property}.",
 "A rider is read as part of the integrated lease. Where a rider and the printed form conflict, the rider controls, because it represents the parties' specific and later-negotiated intent.",
 "The Late Fee Rider assesses a charge of {pct} percent of any installment not received by the {days}th day of the month, together with interest at {pct2} percent per annum on the unpaid balance from the due date.",
 "A late charge and default interest may be imposed cumulatively only where the lease says so expressly. Absent express language, imposing both amounts to a double recovery for the same delay.",
 "The Percentage Rent Rider obligates {defendant} to pay {pct3} percent of annual gross sales in excess of a breakpoint of ${bp}, with 'gross sales' defined to exclude returns, sales taxes collected, and inter-store transfers.",
 "Internet orders fulfilled from the leased premises fall within the definition of gross sales; orders merely placed at a kiosk on the premises and shipped from a remote warehouse do not.",
 "The Continuous Operation Rider requires the tenant to remain open during the hours the shopping center is open. It is enforceable by injunction only where damages are inadequate; a going-dark clause with a stated liquidated remedy displaces injunctive relief.",
 "The Assignment and Subletting Rider conditions transfer on the landlord's consent, 'which shall not be unreasonably withheld.' Reasonableness is measured by objective commercial criteria: the proposed transferee's financial capacity, use, and experience.",
 "A landlord may not withhold consent in order to extract a rent increase not bargained for in the lease. The demand for {pct4} percent of the sublease profits, absent a recapture provision, was unreasonable as a matter of law.",
 "The Holdover Rider fixes holdover rent at {mult} times the last monthly installment. Such a provision is enforceable as liquidated damages where holdover harm is difficult to estimate and the multiplier is not grossly disproportionate.",
 "The Estoppel Rider requires the tenant to deliver a certificate within {days4} days of request. Failure to deliver operates as an admission of the facts stated in the landlord's proposed form only where the rider so provides.",
 "Judgment for {defendant} on the late-fee and default-interest claim is affirmed; judgment for {plaintiff} on the percentage-rent claim is affirmed as modified.",
],
"eminent_domain": [
 "The {county} County Redevelopment Authority condemned {acres} acres owned by {defendant} at {property} for construction of a {usetype}. The sole issue on appeal is the measure of just compensation.",
 "Just compensation is the fair market value of the property taken at the date of taking, measured by the price a willing buyer would pay a willing seller, neither being under compulsion.",
 "Where only part of a parcel is taken, the owner recovers the value of the part taken plus severance damages to the remainder, less any special benefit conferred on the remainder by the project.",
 "The highest and best use of the property is the use to which it may reasonably be put in the reasonably near future. A use dependent on a rezoning is admissible only on a showing that the rezoning was reasonably probable.",
 "The trial court excluded testimony valuing the parcel as {usetype2} land. Given the pending comprehensive-plan amendment and three comparable rezonings in the corridor, the probability showing was made and the exclusion was error.",
 "Evidence of the price paid by the condemnor for neighboring parcels is generally inadmissible, because such sales are made under the shadow of the condemnation power and are not free-market transactions.",
 "The 'scope of the project' rule excludes from the valuation any increase or decrease in value attributable to the project itself, including value changes flowing from the announcement of the project.",
 "Business losses are not compensable as such. Loss of goodwill is recoverable only where a statute so provides; this State's statute permits recovery of relocation expenses of ${spend} but not lost profits.",
 "A taking may be effected without formal proceedings where governmental action substantially deprives the owner of the beneficial use of the land. The {months}-month closure of the only access drive states a claim for inverse condemnation.",
 "Public use is satisfied where the taking serves a legitimate public purpose; the transfer of the condemned land to a private developer under an enforceable redevelopment agreement does not defeat that purpose under this State's constitution.",
 "Interest on the award runs from the date of taking to the date of payment at the statutory rate of {pct} percent, and is a component of just compensation rather than a matter of legislative grace.",
 "The judgment is reversed and the cause remanded for a new trial on valuation with the excluded testimony admitted.",
],
"water_rights": [
 "{plaintiff} and {defendant} own riparian tracts along the {river} within {county} County. The dispute concerns {defendant}'s diversion of approximately {gpm} gallons per minute for irrigation of {acres} acres.",
 "Under the riparian doctrine as modified in this State, each riparian owner is entitled to a reasonable use of the watercourse, measured against the correlative rights of other riparians.",
 "Reasonableness is a question of fact informed by the purpose of the use, its economic and social value, the extent of the harm, the practicality of avoiding the harm, and the protection of existing investments.",
 "A use that wholly deprives a downstream riparian of water for domestic purposes is unreasonable as a matter of law, without regard to the economic value of the upstream use.",
 "Groundwater in this State is governed by the rule of reasonable use, under which an overlying owner may withdraw for beneficial use on the overlying land but may not export off-tract to the injury of neighboring wells.",
 "The {ndays} days of well failure experienced by {plaintiff} coincided with the operation of {defendant}'s high-capacity irrigation well {feet} feet from the shared aquifer boundary. Causation was established by drawdown modeling.",
 "Severed mineral rights carry an implied easement to use so much of the surface as is reasonably necessary to extract the minerals, but that right is qualified by an obligation to accommodate existing surface uses where reasonable alternatives exist.",
 "The accommodation doctrine required {defendant} to consider directional drilling from an off-site pad before siting the wellpad within the irrigated circle. Failure even to evaluate the alternative defeats the claim of reasonable necessity.",
 "Accretion belongs to the riparian owner; avulsion does not change the boundary. The {year0} channel shift, being sudden and perceptible, was avulsive and left the boundary at the former thread of the stream.",
 "A prescriptive water right may be acquired by open, adverse diversion for the statutory period, but only as against a use that was actually interfered with during that period.",
 "The public trust doctrine reserves to the State title to the beds of navigable waters. Navigability for title purposes is determined by susceptibility to commercial navigation at the date of statehood.",
 "The injunction is modified to permit diversion not exceeding {gpm2} gallons per minute between {month1} and {month2}, and is otherwise affirmed.",
],
}


RIDERS: Dict[str, List[Dict[str, str]]] = {
"landlord_tenant": [
 {"heading": "RIDER A — LATE CHARGES AND RETURNED PAYMENTS", "text": "Tenant shall pay a late charge equal to five percent (5%) of the monthly installment for any rent not received by Landlord on or before the {days}th day of the month in which it is due. The late charge is agreed to represent Landlord's administrative cost of processing a delinquent payment and is not a penalty or a charge for the use of money. A returned-payment fee of ${late} shall be assessed for any instrument returned unpaid. No late charge shall be assessed on a late charge, and no default interest shall accrue on any installment for which a late charge has been assessed."},
 {"heading": "RIDER B — HABITABILITY, REPAIRS AND ACCESS", "text": "Landlord shall maintain the heating, plumbing, electrical and structural elements of the Premises in good and safe working order. Tenant shall give Landlord written notice of any condition requiring repair. Landlord shall commence a repair affecting heat, hot water, or sanitation within twenty-four (24) hours of notice and all other repairs within {days2} days. If Landlord fails to commence within those periods, Tenant may, after a second written notice, cause the repair to be made and deduct the reasonable cost, not exceeding one month's rent in any twelve-month period, from the next installment. Nothing in this Rider waives the implied warranty of habitability."},
 {"heading": "RIDER C — SECURITY DEPOSIT", "text": "Landlord holds the sum of ${deposit} as security for Tenant's performance. The deposit shall be held in a segregated interest-bearing account at a federally insured institution located within this State. Within {days3} days after surrender of the Premises, Landlord shall return the deposit together with accrued interest, less any lawful deductions, accompanied by an itemized written statement identifying each deduction and attaching supporting invoices. Failure to furnish the itemized statement within that period forfeits Landlord's right to retain any portion of the deposit."},
 {"heading": "RIDER D — PETS AND ASSISTANCE ANIMALS", "text": "No animal shall be kept on the Premises without Landlord's prior written consent, except that this Rider does not apply to a service animal or to a reasonable accommodation required by fair-housing law, for which no pet deposit or pet rent may be charged. Where consent is granted, Tenant shall pay a refundable pet deposit of ${petdep} and shall be liable for all damage caused by the animal beyond ordinary wear."},
 {"heading": "RIDER E — SUBLETTING AND EARLY TERMINATION", "text": "Tenant may not sublet the Premises or assign this Lease without Landlord's written consent, which shall not be unreasonably withheld or delayed. Tenant may terminate early upon {days4} days' written notice and payment of a termination fee equal to two (2) monthly installments, provided that no termination fee shall be charged where the termination follows Landlord's material breach, a lawful lease-break for domestic violence, or military relocation orders."},
 {"heading": "RIDER F — UTILITY ALLOCATION", "text": "Where utilities are master-metered, Landlord shall allocate charges among units by the ratio of occupied square footage and shall furnish, upon written request, a copy of the master bill and the allocation calculation for any billing period within the preceding twelve months. Landlord shall not impose an administrative markup exceeding {pct} percent of the actual charge."},
],
"easement": [
 {"heading": "RIDER 1 — GRANT AND DESCRIPTION OF EASEMENT", "text": "Grantor grants to Grantee, its successors and assigns, a perpetual non-exclusive easement {feet} feet in width for ingress, egress and utilities over and across the northerly portion of the Servient Estate, the centerline of which is the existing gravel drive as it presently exists on the ground. This easement is appurtenant to and runs with the Dominant Estate and may not be conveyed separately from it."},
 {"heading": "RIDER 2 — MAINTENANCE AND COST ALLOCATION", "text": "Grantee shall maintain the easement area in a condition reasonably suited to its use, including grading, gravel replenishment and culvert clearing. Where the easement is used by more than one dominant owner, maintenance costs shall be shared in proportion to use, and any owner advancing more than its share may recover contribution. Grantor shall not be required to contribute to maintenance occasioned by Grantee's use."},
 {"heading": "RIDER 3 — SCOPE LIMITATION AND GATES", "text": "Use of the easement is limited to passenger vehicles, light trucks and agricultural equipment consistent with the historic use of the way. Commercial haul traffic, quarry traffic and use in connection with any subdivision of the Dominant Estate into more than {units} lots are outside the scope of this grant. Grantor may install gates at the points of entry provided that no gate shall be locked against Grantee and any lock installed shall be keyed to Grantee as well."},
 {"heading": "RIDER 4 — RELOCATION", "text": "Grantor may relocate the easement at Grantor's sole cost upon {days4} days' written notice, provided the relocated way is of equal width and grade, provides equal utility and access, and does not increase the distance of travel by more than {pct} percent. Grantee's consent shall not be unreasonably withheld."},
 {"heading": "RIDER 5 — TERMINATION AND NON-ABANDONMENT", "text": "This easement terminates only by written release recorded in the land records, by merger of the dominant and servient estates in a single owner, or by a court decree. Non-use, however long continued, shall not constitute abandonment absent a recorded release or an affirmative act by Grantee manifesting an intent permanently to relinquish the right."},
],
"boundary_title": [
 {"heading": "RIDER I — BOUNDARY LINE AGREEMENT", "text": "The parties, being uncertain as to the true location of their common boundary, agree that the line established by the existing fence, as located and monumented by the survey of record dated {surveydate}, is and shall be the boundary between their respective parcels for all purposes. Each party quitclaims to the other all right, title and interest lying on the other's side of the agreed line. This agreement shall be recorded and shall bind the parties' successors."},
 {"heading": "RIDER II — SURVEY AND MONUMENTATION", "text": "The agreed line shall be monumented with iron pins set at each angle point and at intervals not exceeding {feet} feet, and a plat of the survey shall be filed with the {county} County Recorder. In the event of conflict between this description and the monuments as set, the monuments shall control."},
 {"heading": "RIDER III — TITLE WARRANTIES AND EXCEPTIONS", "text": "The conveyance is made subject to: (a) all easements, restrictions and reservations of record; (b) the rights of parties in possession as disclosed by an accurate survey; (c) real property taxes for the current year, prorated as of closing; and (d) the encroachment of the {struct} across the common line as shown on the survey. Grantor's warranty of title excepts each of the foregoing."},
 {"heading": "RIDER IV — ENCROACHMENT LICENSE", "text": "The parties acknowledge that the {struct} encroaches approximately {feet2} feet onto the adjoining parcel. The adjoining owner grants a revocable license permitting the encroachment to remain until the structure is removed, destroyed, or substantially rebuilt, at which time the license terminates automatically and the structure shall be reconstructed wholly within the boundary."},
 {"heading": "RIDER V — MUTUAL RELEASE AND QUIET ENJOYMENT", "text": "Each party releases the other from all claims for trespass, ejectment, or damage to the disputed strip arising before the date of this agreement, and covenants not to disturb the other's quiet enjoyment of the land lying on that party's side of the agreed line."},
],
"hoa_covenant": [
 {"heading": "RIDER 1 — ARCHITECTURAL REVIEW PROCEDURE", "text": "No structure, addition, fence, or exterior alteration shall be commenced until plans have been submitted to and approved in writing by the Architectural Review Committee. The Committee shall act within {days4} days of a complete submission; failure to act within that period constitutes approval. Any denial shall be in writing and shall identify the specific provision of the Declaration or published guideline on which it rests. Approval may not be withheld on grounds of personal taste alone."},
 {"heading": "RIDER 2 — ASSESSMENTS, LIENS AND PRIORITY", "text": "Annual assessments are levied against each Lot in equal shares and are due on the first day of each fiscal year. Unpaid assessments bear interest at {pct2} percent per annum and become a lien upon recording of a notice of assessment lien in the {county} County land records. The lien is subordinate to a first mortgage of record predating the notice and superior to all other subsequently recorded encumbrances. The Association shall furnish an estoppel statement of amounts due within {days} days of written request."},
 {"heading": "RIDER 3 — ENFORCEMENT, FINES AND HEARING RIGHTS", "text": "Before imposing any fine, the Board shall give the owner written notice of the alleged violation and an opportunity to be heard before the Board or a committee of at least three members who are not officers. Fines shall not exceed ${fines} per violation nor ${fines2} in the aggregate for a continuing violation. A fine imposed without the notice and hearing required by this Rider is void."},
 {"heading": "RIDER 4 — LEASING RESTRICTION", "text": "No Lot may be leased for a term of less than {months} months, and no more than {pct3} percent of the Lots may be leased at any one time. An owner in possession on the date this Rider was recorded is exempt as to that Lot until title is transferred. This Rider does not apply to a lease to a family member of the owner or to occupancy incident to a mortgagee's possession following foreclosure."},
 {"heading": "RIDER 5 — MAINTENANCE ALLOCATION AND RESERVES", "text": "The Association maintains the common areas, private drives and stormwater facilities. The owner maintains the Lot and all structures on it, including roofs, windows and exterior doors. The Board shall commission a reserve study not less often than every {years} years and shall fund reserves at not less than {pct4} percent of the study's recommended annual contribution."},
],
"foreclosure": [
 {"heading": "RIDER A — NOTICE OF DEFAULT AND RIGHT TO CURE", "text": "Before accelerating the indebtedness, Lender shall mail to Borrower at Borrower's last known address a notice specifying: (a) the default; (b) the action required to cure it; (c) a date not less than {days} days from the date the notice is mailed by which the default must be cured; (d) that failure to cure by that date may result in acceleration and sale of the Property; and (e) Borrower's right to reinstate after acceleration and to assert in the foreclosure proceeding the non-existence of a default. Strict compliance with this Rider is a condition precedent to acceleration."},
 {"heading": "RIDER B — LOSS MITIGATION AND TRIAL PLAN", "text": "Upon receipt of a complete loss-mitigation application more than {days3} days before a scheduled sale, Servicer shall evaluate the application for all available alternatives to foreclosure and shall not move for judgment or conduct a sale while the evaluation is pending. Where Borrower makes all payments required by a trial plan, Servicer shall offer a permanent modification on the terms the trial plan describes, and may not deny the modification on a ground that was known and could have been raised before the trial plan was offered."},
 {"heading": "RIDER C — ESCROW ACCOUNT", "text": "Borrower shall pay monthly into escrow one-twelfth of the annual taxes and insurance premiums. Servicer shall conduct an annual escrow analysis and shall furnish Borrower a statement identifying any shortage or surplus. A shortage of ${escrow} or less shall be spread over not fewer than twelve monthly installments and shall not, standing alone, constitute a default."},
 {"heading": "RIDER D — SALE, DEFICIENCY AND SURPLUS", "text": "Any sale shall be conducted publicly after publication for {weeks} consecutive weeks. No deficiency judgment shall be entered unless the court finds, after an evidentiary hearing, that the sale price was commercially reasonable in relation to the fair market value of the Property. Any surplus remaining after satisfaction of the debt, costs and junior liens of record shall be paid to Borrower within {days2} days of confirmation."},
 {"heading": "RIDER E — TENANT PROTECTIONS AFTER SALE", "text": "A purchaser at the sale takes subject to any bona fide tenancy in existence at the time of the notice of sale. The purchaser shall give a bona fide tenant not less than {days4} days' written notice to vacate, and a tenant under a bona fide lease may occupy the Property for the remaining term of the lease unless the purchaser will occupy the Property as a primary residence."},
],
"adverse_possession": [
 {"heading": "RIDER 1 — STATEMENT OF CLAIM AND DESCRIPTION", "text": "Claimant asserts title by adverse possession to a tract of {acres} acres more particularly described in the surveyor's Exhibit {ex}, being that portion of the record parcel lying east of the posted line and north of the old rail grade, and claims the same in fee simple absolute as against all persons."},
 {"heading": "RIDER 2 — ACTS OF POSSESSION RELIED UPON", "text": "Claimant relies upon the following acts, each continuing from the date shown through the date of filing: posting of the perimeter against trespass beginning in {year0}; commercial timber harvest in {year1} and {year2}; construction and continuous seasonal use of a hunting camp; annual maintenance of the interior access track; and payment of the real property taxes assessed against the tract for {ntax} of the {years} years preceding this claim."},
 {"heading": "RIDER 3 — TACKING AND PRIVITY", "text": "Claimant tacks to its own possession the {years2} years of possession of its immediate predecessor in interest, with whom Claimant is in privity by virtue of the deed recorded at Book {bk}, Page {pg}, which deed purported to convey the disputed tract and thereby transferred the possessory claim along with the record title."},
 {"heading": "RIDER 4 — EXCLUSIONS FROM CLAIM", "text": "This claim expressly excludes: (a) any land held by the municipality or the State for a public purpose, including the {feet}-foot platted right of way; (b) any land subject to a recorded easement, as to which Claimant asserts no interest inconsistent with the easement; and (c) any subsurface mineral estate previously severed of record."},
 {"heading": "RIDER 5 — QUIET TITLE RELIEF REQUESTED", "text": "Claimant requests a decree quieting title in Claimant as against Respondent and all persons claiming under Respondent, describing the vested tract by metes and bounds, directing the Recorder to index the decree against both parcels, and awarding costs. Claimant does not seek damages for the period of possession."},
],
"zoning": [
 {"heading": "RIDER A — VARIANCE APPLICATION AND FINDINGS REQUIRED", "text": "An application for a use variance shall be granted only upon written findings, supported by substantial evidence in the record, that: (1) the property cannot yield a reasonable return in any use permitted in the district; (2) the hardship arises from conditions unique to the parcel and not generally applicable in the district; (3) the hardship was not self-created; and (4) the variance will not alter the essential character of the locality. Findings that merely recite the language of this Rider without reference to record evidence are insufficient."},
 {"heading": "RIDER B — CONDITIONS OF APPROVAL", "text": "Any approval is subject to the following conditions, each of which runs with the land: hours of operation limited to {hours}; off-street parking of not fewer than {spaces} spaces; a landscaped buffer of not less than {feet} feet along every boundary abutting a residential district; exterior lighting shielded and directed downward; and no exterior signage exceeding {sqft2} square feet. Violation of any condition voids the approval after notice and an opportunity to cure."},
 {"heading": "RIDER C — NONCONFORMING USE AND ABANDONMENT", "text": "A use lawfully existing on the effective date of this ordinance may continue in its then-existing scope but shall not be enlarged, extended to additional land, or changed to another nonconforming use. Discontinuance of the use for {months} consecutive months creates a rebuttable presumption of abandonment, which may be overcome by evidence of an intent to resume together with overt acts consistent with that intent."},
 {"heading": "RIDER D — VESTED RIGHTS AND MORATORIUM", "text": "A permittee who, in good-faith reliance on a validly issued permit, has incurred substantial expenditures or substantially changed position acquires a vested right to complete the development in accordance with the permit, notwithstanding any subsequently adopted ordinance or moratorium. Expenditures for architectural, engineering and permitting services alone are not 'substantial' for purposes of this Rider unless they exceed {pct} percent of the total project cost."},
 {"heading": "RIDER E — APPEAL AND EXHAUSTION", "text": "Any person aggrieved may appeal to the Board within {days4} days of the decision, and thereafter to the {state} courts within thirty days of the Board's written decision. Administrative remedies must be exhausted before judicial review is sought, except that a facial challenge to the constitutionality of the ordinance may be brought directly."},
],
"lease_rider": [
 {"heading": "RIDER 1 — LATE FEES AND DEFAULT INTEREST", "text": "If any installment of Base Rent or Additional Rent is not received by Landlord by the {days}th day of the month, Tenant shall pay a late charge equal to {pct} percent of the overdue installment. Amounts remaining unpaid more than thirty (30) days after the due date shall thereafter bear interest at {pct2} percent per annum. The late charge and default interest are alternative and not cumulative remedies for the same delinquent installment; in no event shall Tenant be charged both for the same period of delay."},
 {"heading": "RIDER 2 — PERCENTAGE RENT", "text": "In addition to Base Rent, Tenant shall pay {pct3} percent of Gross Sales in each Lease Year in excess of a breakpoint of ${bp}. 'Gross Sales' means all receipts from business conducted at, from, or fulfilled out of the Premises, whether for cash or credit, and expressly includes internet and telephone orders fulfilled from inventory located at the Premises, and expressly excludes: returns and allowances actually credited; sales, excise and similar taxes collected and remitted; transfers of merchandise to other stores of Tenant not made to avoid percentage rent; and receipts from vending machines maintained for employees. Tenant shall deliver a statement of Gross Sales within {days3} days after each Lease Year, and Landlord may audit not more than once per Lease Year."},
 {"heading": "RIDER 3 — ASSIGNMENT, SUBLETTING AND RECAPTURE", "text": "Tenant shall not assign this Lease or sublet all or any part of the Premises without Landlord's prior written consent, which shall not be unreasonably withheld, conditioned or delayed. Landlord's consent shall be deemed reasonable if based on the proposed transferee's financial condition, business reputation, proposed use, or the compatibility of that use with the tenant mix of the Center. Upon request for consent to an assignment of the entire Premises, Landlord may elect within {days4} days to recapture the Premises and terminate this Lease. Absent such recapture election, Landlord shall not condition consent upon payment of any portion of the transfer consideration in excess of {pct4} percent of the profit remaining after Tenant's reasonable transaction costs."},
 {"heading": "RIDER 4 — CONTINUOUS OPERATION AND GOING DARK", "text": "Tenant shall continuously operate the Premises under its trade name during the hours the Center is open. If Tenant ceases operations for more than {days2} consecutive days other than for remodeling, casualty, or force majeure, Landlord's sole remedies shall be (a) to collect substitute rent equal to {mult} times Base Rent for each month of closure, and (b) to terminate this Lease on thirty days' notice. The parties agree that these remedies are adequate and that Landlord shall not be entitled to specific performance of this Rider."},
 {"heading": "RIDER 5 — HOLDOVER", "text": "If Tenant remains in possession after expiration without Landlord's written consent, the tenancy shall be one at sufferance terminable at will, and Tenant shall pay for each month or portion of a month of holding over an amount equal to {mult} times the Base Rent last payable, together with all Additional Rent. The parties agree that the harm from a holdover is difficult to estimate and that this amount is a reasonable forecast of that harm and not a penalty."},
 {"heading": "RIDER 6 — ESTOPPEL CERTIFICATES AND SUBORDINATION", "text": "Within {days4} days after written request, Tenant shall execute and deliver a certificate stating the commencement and expiration dates, the amount of Base Rent, the amounts of any prepaid rent and security deposit, and whether to Tenant's knowledge Landlord is in default. Failure to deliver within that period shall be deemed an admission of the accuracy of the statements contained in the form furnished by Landlord. This Lease is subordinate to any mortgage now or hereafter placed on the Center, provided the mortgagee delivers a commercially reasonable non-disturbance agreement."},
],
"eminent_domain": [
 {"heading": "RIDER 1 — DESCRIPTION OF THE TAKING", "text": "The Condemnor takes in fee simple {acres} acres out of the Owner's parcel of {acres2} acres, together with a temporary construction easement of {feet} feet in width along the taking line for a term of {months} months, for the purpose of constructing the {usetype}. The date of taking is the date of the deposit of estimated compensation with the clerk."},
 {"heading": "RIDER 2 — MEASURE OF JUST COMPENSATION", "text": "Compensation shall be the fair market value of the part taken, determined as of the date of taking, plus damages to the remainder resulting from the taking and from the construction and use of the project as planned, less the value of any special benefit conferred on the remainder. General benefits shared with the community at large shall not be offset. Value shall be determined with reference to the highest and best use, which may include a use requiring a rezoning where the rezoning is reasonably probable."},
 {"heading": "RIDER 3 — EXCLUDED EVIDENCE", "text": "The following are not admissible on the issue of value: the price paid by the Condemnor for other parcels acquired for this project; any increase or decrease in value attributable to the project itself or to its announcement; offers to purchase not accepted; and the assessed valuation for property tax purposes."},
 {"heading": "RIDER 4 — RELOCATION AND BUSINESS LOSSES", "text": "The Owner is entitled to actual and reasonable moving expenses, expenses of searching for a replacement site not exceeding ${spend}, and reestablishment expenses. Loss of business profits and loss of goodwill are not compensable except to the extent expressly provided by statute. Payment of relocation benefits is not an offset against just compensation."},
 {"heading": "RIDER 5 — INTEREST, POSSESSION AND ABANDONMENT", "text": "Interest at {pct} percent per annum accrues on the difference between the deposit and the final award from the date of taking to the date of payment, as a constitutional component of just compensation. The Condemnor may take possession upon deposit. If the Condemnor abandons the taking before final judgment, it shall pay the Owner's reasonable costs, appraisal fees and attorney's fees actually incurred."},
],
"water_rights": [
 {"heading": "RIDER A — DIVERSION LIMITS AND SEASONAL SCHEDULE", "text": "The Upper Owner may divert from the {river} for irrigation not more than {gpm} gallons per minute, and not more than an aggregate of {af} acre-feet in any calendar year. Between {month1} and {month2} the permitted rate is reduced to {gpm2} gallons per minute. No diversion is permitted whenever the gauged flow at the {county} County station falls below the minimum bypass flow set out in Rider B."},
 {"heading": "RIDER B — MINIMUM BYPASS FLOW AND MEASUREMENT", "text": "A minimum bypass flow sufficient to satisfy downstream domestic and stock-watering needs shall be maintained at all times. Each diverting party shall install and maintain a totalizing meter at the point of diversion, shall record readings weekly, and shall furnish records to any other riparian owner within {days} days of written request. Domestic use has priority over irrigation, and irrigation over industrial use, in every period of shortage."},
 {"heading": "RIDER C — GROUNDWATER AND WELL INTERFERENCE", "text": "No high-capacity well shall be completed within {feet} feet of an existing domestic well without a drawdown analysis furnished to the affected owner. If operation of a high-capacity well causes an existing domestic well to fail or its yield to fall below five gallons per minute, the operator shall, at its expense, deepen or replace the affected well or provide an equivalent permanent supply. Withdrawal for export off the overlying tract is prohibited where it injures a neighboring overlying user."},
 {"heading": "RIDER D — SEVERED MINERAL ESTATE AND SURFACE ACCOMMODATION", "text": "The owner of the severed mineral estate may use so much of the surface as is reasonably necessary for exploration and production, and shall accommodate existing surface uses where a reasonable alternative means of extraction exists. Before siting any wellpad within an irrigated area, the operator shall evaluate in writing off-site and directional alternatives and shall furnish that evaluation to the surface owner not less than {days4} days before entry."},
 {"heading": "RIDER E — BOUNDARY, ACCRETION AND PUBLIC TRUST", "text": "Where the boundary is a watercourse, gradual accretion and reliction move the boundary with the water; a sudden and perceptible avulsive change does not, and the boundary remains at the former thread of the stream. Nothing in this instrument conveys any interest in the bed of a navigable water, title to which is held by the State in trust for the public."},
],
}


# General clause bank — short operative provisions attached to any case type.
CLAUSES: List[Dict[str, str]] = [
 {"heading": "Governing Law", "text": "This instrument shall be governed by and construed in accordance with the laws of the State of {state}, without regard to its conflict-of-laws principles. Any action arising out of or relating to this instrument shall be brought exclusively in the courts sitting in {county} County, {state}, and each party consents to the personal jurisdiction of those courts."},
 {"heading": "Notice", "text": "Every notice required or permitted shall be in writing and shall be deemed given: on personal delivery; on the third business day after deposit in the United States mail, certified, return receipt requested, postage prepaid; or on the next business day after deposit with a nationally recognized overnight courier. Notices to a party shall be sent to the address last furnished by that party in writing. Electronic mail alone does not constitute notice unless the recipient acknowledges receipt in writing."},
 {"heading": "Recording", "text": "This instrument shall be recorded in the land records of {county} County, {state}, and shall run with the land, binding upon and inuring to the benefit of the parties and their respective heirs, successors, personal representatives and assigns. The party causing the instrument to be recorded shall bear the recording fees and shall furnish a conformed copy to the other party within {days} days of recording."},
 {"heading": "Attorney's Fees", "text": "In any action to enforce or construe this instrument, the prevailing party shall recover its reasonable attorney's fees, expert fees and costs, at trial and on appeal. Where the instrument grants fees to one party only, this clause shall be read as reciprocal and shall entitle the other party to fees on the same terms if that party prevails."},
 {"heading": "Severability", "text": "If any provision of this instrument is held invalid, illegal, or unenforceable, that provision shall be reformed to the minimum extent necessary to render it enforceable, and if it cannot be so reformed it shall be severed, and the remaining provisions shall continue in full force and effect."},
 {"heading": "Waiver and Course of Dealing", "text": "No waiver of any breach shall be effective unless in writing and signed by the party charged. The acceptance of a payment with knowledge of a breach, the failure to insist on strict performance, or any course of dealing between the parties shall not constitute a waiver of that or any subsequent breach, nor estop the party from enforcing the provision thereafter."},
 {"heading": "Entire Agreement and Riders", "text": "This instrument, together with the exhibits and riders attached and incorporated by reference, constitutes the entire agreement of the parties and supersedes all prior negotiations, representations and agreements, whether oral or written. In the event of a conflict between a printed provision and a rider, the rider shall control, the rider being the specifically negotiated expression of the parties' intent."},
 {"heading": "Time of the Essence", "text": "Time is of the essence as to every obligation stated in this instrument. Where the final day for performance falls on a Saturday, Sunday, or legal holiday in the State of {state}, the period is extended to the next business day."},
 {"heading": "Force Majeure", "text": "Neither party shall be liable for a failure of performance, other than an obligation to pay money, caused by an act of God, flood, fire, civil disturbance, governmental order, epidemic, or other cause beyond that party's reasonable control, provided the affected party gives notice within {days} days and resumes performance as promptly as practicable."},
 {"heading": "Inspection and Right of Entry", "text": "Upon not less than twenty-four (24) hours' prior notice, and at reasonable times, a party may enter upon the subject premises to inspect, to make permitted repairs, or to show the premises to a prospective purchaser or lender. Entry without notice is permitted only in an emergency threatening life or substantial property damage, and the entering party shall give notice of the entry as soon as practicable thereafter."},
 {"heading": "Indemnity", "text": "Each party shall indemnify, defend and hold harmless the other from all claims, damages and expenses, including reasonable attorney's fees, arising out of that party's use of the subject premises or breach of this instrument, except to the extent caused by the negligence or willful misconduct of the party seeking indemnity. This clause survives termination."},
 {"heading": "Insurance", "text": "The party in possession shall maintain commercial general liability insurance of not less than ${insurance} per occurrence, naming the other party as an additional insured, and shall furnish a certificate of insurance on request and on each renewal. Each party waives subrogation against the other to the extent of insurance proceeds actually received."},
 {"heading": "Dispute Resolution", "text": "Before filing suit, a party shall give written notice of the dispute and the parties shall confer in good faith for not fewer than {days} days, and shall thereafter submit the dispute to non-binding mediation before a mediator experienced in real property matters. This clause does not bar an action for injunctive relief to prevent irreparable harm or an action to preserve the status quo."},
 {"heading": "Successors, Assigns and Runs With the Land", "text": "The benefits and burdens created by this instrument touch and concern the subject land, are intended by the parties to run with the land in perpetuity, and bind every successor in title with notice, actual, constructive or inquiry. A conveyance of the benefited parcel carries the benefit whether or not this instrument is mentioned in the deed of conveyance."},
 {"heading": "Counterparts and Electronic Signature", "text": "This instrument may be executed in counterparts, each of which is an original and all of which together constitute one instrument. A signature delivered electronically has the same effect as an original, provided that any instrument submitted for recording shall bear original signatures and acknowledgment before a notary public of the State of {state}."},
 {"heading": "Interpretation and Construction Against Drafter", "text": "Headings are for convenience only and do not affect construction. The singular includes the plural. This instrument is the product of negotiation between the parties, and no rule of construction requiring interpretation against the drafting party shall apply. Restrictions on the use of land shall nonetheless be construed in favor of the free use of the land."},
]


# --------------------------------------------------------------- slot filling
def _slots(rng: random.Random, state: str, county: str) -> Dict[str, Any]:
    """Build the substitution dictionary for one case. Every template slot used
    anywhere in the banks must have a key here."""
    y0 = rng.randint(1972, 2008)
    return {
        "state": state,
        "county": county,
        "street": rng.choice(STREETS),
        "river": rng.choice(["Kestrel River", "Mill Race Creek", "Sable Fork",
                             "Thornfield Run", "Brightwater Branch"]),
        "subdiv": rng.choice(ENTITY_ROOTS),
        "units": rng.choice([4, 6, 8, 12, 18, 24]),
        "unit": f"{rng.randint(1,4)}{rng.choice('ABCD')}",
        "year0": y0,
        "year1": y0 + rng.randint(5, 14),
        "year2": y0 + rng.randint(15, 26),
        "year3": y0 + rng.randint(27, 34),
        "leasedate": f"{rng.choice(['January','March','June','September'])} {rng.randint(1,28)}, {y0 + rng.randint(20, 36)}",
        "noticedate": f"{rng.choice(['February','April','July','October'])} {rng.randint(1,28)}, {y0 + rng.randint(22, 38)}",
        "noticedate2": f"{rng.choice(['May','August','November'])} {rng.randint(1,28)}, {y0 + rng.randint(22, 38)}",
        "repairdate": f"{rng.choice(['March','June','December'])} {rng.randint(1,28)}, {y0 + rng.randint(22, 38)}",
        "surveydate": f"{rng.choice(['January','April','September'])} {rng.randint(1,28)}, {y0 + rng.randint(18, 34)}",
        "month1": rng.choice(["January", "February", "March", "April", "May", "June"]),
        "month2": rng.choice(["July", "August", "September", "October", "November"]),
        "rent": f"{rng.randrange(850, 3200, 25):,}",
        "late": f"{rng.choice([35, 50, 75, 100, 125, 150])}",
        "deposit": f"{rng.randrange(800, 4000, 50):,}",
        "petdep": f"{rng.choice([200, 250, 300, 400, 500])}",
        "fees": f"{rng.randrange(2000, 24000, 500):,}",
        "fines": f"{rng.choice([50, 100, 150, 250, 500])}",
        "fines2": f"{rng.choice([1000, 1500, 2500, 5000]):,}",
        "principal": f"{rng.randrange(120000, 780000, 5000):,}",
        "escrow": f"{rng.randrange(300, 4200, 50):,}",
        "bid": f"{rng.randrange(90000, 400000, 5000):,}",
        "appraised": f"{rng.randrange(180000, 700000, 5000):,}",
        "spend": f"{rng.randrange(15000, 900000, 5000):,}",
        "bp": f"{rng.randrange(200000, 2000000, 25000):,}",
        "insurance": f"{rng.choice([500000, 1000000, 2000000]):,}",
        "days": rng.choice([3, 5, 7, 10, 15]),
        "days2": rng.choice([14, 21, 30, 45]),
        "days3": rng.choice([14, 21, 30, 45, 60]),
        "days4": rng.choice([30, 45, 60, 90]),
        "ndays": rng.randint(9, 120),
        "months": rng.choice([6, 9, 12, 18, 24]),
        "weeks": rng.choice([3, 4, 6]),
        "years": rng.choice([7, 10, 15, 20, 21]),
        "years2": rng.randint(4, 12),
        "pct": rng.choice([3, 5, 8, 10, 15]),
        "pct2": rng.choice([6, 9, 12, 18]),
        "pct3": rng.choice([2, 3, 4, 5, 6]),
        "pct4": rng.choice([25, 50, 75, 100]),
        "mult": rng.choice(["1.5", "two (2)", "1.25", "three (3)"]),
        "feet": rng.choice([12, 16, 20, 25, 30, 40, 50]),
        "feet2": rng.choice(["1.5", "2.3", "3.8", "4.1", "6.7"]),
        "acres": rng.choice(["1.4", "2.7", "5.2", "8.9", "12.5", "17.3", "24.0"]),
        "acres2": rng.choice(["3.1", "6.8", "11.4", "22.6", "40.2"]),
        "sqft": f"{rng.randrange(140, 1400, 20):,}",
        "sqft2": rng.choice([12, 16, 24, 32]),
        "gpm": f"{rng.randrange(150, 1800, 25):,}",
        "gpm2": f"{rng.randrange(50, 400, 25):,}",
        "af": f"{rng.randrange(20, 900, 10):,}",
        "zone": rng.choice(["1", "2", "3", "1A", "2B"]),
        "sec": f"{rng.randint(3, 19)}.{rng.randint(1, 9)}",
        "art": rng.choice(["III", "IV", "V", "VII", "IX", "XI"]),
        "art2": rng.choice(["VI", "VIII", "X", "XII"]),
        "ex": rng.choice(["A", "B", "C", "D-1", "E-2"]),
        "bk": rng.randrange(400, 9800),
        "pg": rng.randrange(10, 990),
        "ntax": rng.randint(5, 20),
        "npay": rng.randint(3, 14),
        "n_viol": rng.randint(3, 22),
        "hours": rng.choice(["7:00 a.m. to 7:00 p.m.", "8:00 a.m. to 6:00 p.m.",
                             "6:00 a.m. to 10:00 p.m."]),
        "spaces": rng.choice([6, 12, 20, 34, 48]),
        "struct": rng.choice(["detached garage", "board fence", "equipment shed",
                              "retaining wall", "carport"]),
        "usetype": rng.choice(["veterinary clinic", "self-storage facility",
                               "day-care center", "microbrewery taproom",
                               "regional stormwater basin", "transit maintenance yard",
                               "county recycling transfer station"]),
        "usetype2": rng.choice(["light-industrial", "highway-commercial",
                                "multifamily residential"]),
        "bear1": f"{rng.randint(10,89)}\u00b0{rng.randint(1,59):02d}'",
        "bear2": f"{rng.randint(10,89)}\u00b0{rng.randint(1,59):02d}'",
        "oldroad": rng.choice(["Old Quarry Turnpike", "the Wicklow town road",
                               "the abandoned rail grade", "County Route 12"]),
    }


def _person(rng: random.Random) -> str:
    return f"{rng.choice(FIRST_NAMES)} {rng.choice(SURNAMES)}"


def _entity(rng: random.Random) -> str:
    return rng.choice(ENTITY_FORMS).format(n=rng.choice(ENTITY_ROOTS))


def _party(rng: random.Random) -> str:
    return _entity(rng) if rng.random() < 0.5 else _person(rng)


def _address(rng: random.Random, county: str, state_abbr: str) -> str:
    return f"{rng.randrange(12, 4890)} {rng.choice(STREETS)}, {county}, {state_abbr}"


def _short_name(full: str) -> str:
    """Surname / entity root used in the case caption."""
    if "," in full:
        full = full.split(",")[0]
    parts = full.split()
    return parts[-1] if len(parts) == 2 and parts[0] in FIRST_NAMES else " ".join(parts[:2])


# --------------------------------------------------------------- case builder
def build_case(idx: int, rng: random.Random) -> Dict[str, Any]:
    case_type = CASE_TYPES[idx % len(CASE_TYPES)]
    state, abbr = rng.choice(STATES)
    county = rng.choice(COUNTIES)
    court = rng.choice(COURT_FORMS).format(
        state=state, county=county,
        n=rng.choice(["First", "Second", "Third", "Fourth"]),
    )

    plaintiff = _party(rng)
    defendant = _party(rng)
    while _short_name(defendant) == _short_name(plaintiff):
        defendant = _party(rng)

    prop = _address(rng, county, abbr)
    slots = _slots(rng, state, county)
    slots.update({"plaintiff": plaintiff, "defendant": defendant, "property": prop})

    decided = date(2004, 1, 1) + timedelta(days=rng.randint(0, 8000))
    case_id = f"SYN-{case_type.upper().replace('_','')[:6]}-{idx:04d}"
    case_name = f"{_short_name(plaintiff)} v. {_short_name(defendant)}"

    def fill(t: str) -> str:
        return t.format(**slots)

    sections: List[Dict[str, Any]] = []
    order = 0

    # --- numbered paragraphs (the body of the opinion) -------------------
    bank = PARAGRAPHS[case_type]
    n_par = rng.randint(8, min(12, len(bank)))
    chosen = bank[:1] + rng.sample(bank[1:-1], n_par - 2) + bank[-1:]
    for i, tpl in enumerate(chosen, start=1):
        order += 1
        sections.append({
            "section_type": "paragraph",
            "section_number": str(i),
            "heading": f"Paragraph {i}",
            "order": order,
            "text": fill(tpl),
        })

    # --- riders / addenda ------------------------------------------------
    rbank = RIDERS[case_type]
    for r in sorted(rng.sample(rbank, rng.randint(1, min(3, len(rbank)))),
                    key=lambda d: d['heading']):
        order += 1
        label = r["heading"].split("—")[0].strip()
        sections.append({
            "section_type": "rider",
            "section_number": label,
            "heading": r["heading"],
            "order": order,
            "text": fill(r["text"]),
        })

    # --- clauses ---------------------------------------------------------
    for j, c in enumerate(rng.sample(CLAUSES, rng.randint(2, 4)), start=1):
        order += 1
        sections.append({
            "section_type": "clause",
            "section_number": f"{j}",
            "heading": f"Clause {j} — {c['heading']}",
            "order": order,
            "text": fill(c["text"]),
        })

    return {
        "case_id": case_id,
        "case_name": case_name,
        "full_caption": f"{plaintiff}, Appellant, v. {defendant}, Appellee",
        "court": court,
        "jurisdiction": state,
        "date": decided.isoformat(),
        "case_type": case_type,
        "case_type_label": CASE_TYPE_LABELS[case_type],
        "source": "synthetic",
        "docket_number": f"SYN-{decided.year}-{rng.randrange(1000,9999)}",
        "property_address": prop,
        "fictional_notice": FICTIONAL_NOTICE,
        "sections": sections,
    }


def build_corpus(n_cases: int = 120, seed: int = 20260830,
                 out_dir: Path | None = None) -> List[Path]:
    """Generate ``n_cases`` synthetic cases as one JSON file each. Returns paths."""
    from config import CASES_DIR  # local import keeps this module importable alone

    out_dir = Path(out_dir) if out_dir else CASES_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    written: List[Path] = []
    for i in range(n_cases):
        case = build_case(i, rng)
        p = out_dir / f"{case['case_id']}.json"
        p.write_text(json.dumps(case, indent=2, ensure_ascii=False), encoding="utf-8")
        written.append(p)
    return written


if __name__ == "__main__":
    import argparse, sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    ap = argparse.ArgumentParser(description="Generate the synthetic case corpus.")
    ap.add_argument("-n", "--n-cases", type=int, default=120)
    ap.add_argument("--seed", type=int, default=20260830)
    a = ap.parse_args()
    paths = build_corpus(a.n_cases, a.seed)
    print(f"Wrote {len(paths)} synthetic cases to {paths[0].parent}")
