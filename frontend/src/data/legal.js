// Draft legal copy. Bracketed [ ] items are company details to fill in; have counsel review before launch.
export const EFFECTIVE_DATE = '2026-10-18'

export const TERMS = {
  form: 'HBK-LEGAL-01',
  title: 'Terms and conditions',
  lead: 'These terms govern your use of Hibanako, the quality traceability service that reads fabrication records, links them, and reports what is missing before release.',
  sections: [
    {
      title: 'Agreement',
      body: [
        'By creating an account, signing in or using Hibanako you agree to these terms on behalf of yourself and the organisation you represent. If you do not agree, do not use the service.',
        'Hibanako is provided by [Company legal name], [registered address] ("we", "us"). Where your organisation has signed an order form or master agreement with us, that agreement takes precedence over these terms where they conflict.',
      ],
    },
    {
      title: 'The service',
      body: [
        'Hibanako lets you upload quality documents such as material certificates, weld records, NDT reports, inspection plans and travelers. The service extracts data from them, links the records into a traceability map, runs rule-based checks and produces a release-readiness report.',
        'We may change, improve or discontinue features. We will give reasonable notice before removing functionality your organisation relies on.',
      ],
    },
    {
      title: 'Engineering responsibility',
      body: [
        'Hibanako is a decision-support tool. Verdicts such as ACCEPTABLE, NOT ACCEPTABLE and INCOMPLETE come from rules applied to the extracted data, and explanations are generated automatically for review. Neither replaces the judgement of a qualified engineer or inspector.',
        'Release decisions, concessions and sign-offs are made by your personnel. You remain responsible for verifying extracted values against the source documents, for the accuracy of the records you upload, and for compliance with the codes, standards and contracts that apply to your work.',
        'Clause references and limits in our rule sets are summaries. They are not copies of the standards, may not reflect the edition or addenda in your contract, and must be confirmed by you against the governing documents.',
        'Hibanako is not a certification body, notified body, classification society or third-party inspection agency. Reports are not certificates of conformity and must not be presented as one.',
      ],
    },
    {
      title: 'Safety-critical use',
      body: [
        'Welded products such as pressure equipment, piping, hulls and lifting structures can cause serious harm if they fail. You must not rely on Hibanako as the only control on the quality or safety of any product. Your inspection, testing and approval processes remain in force whether or not you use the service.',
      ],
    },
    {
      title: 'Accounts',
      body: [
        'You must keep your sign-in credentials confidential and tell us promptly about any unauthorised use. You are responsible for activity under your account and for the users your organisation invites.',
      ],
    },
    {
      title: 'Your data',
      body: [
        'You keep all rights to the documents and data you upload ("Customer Data"). You grant us a limited licence to host, copy, process and display Customer Data only as needed to provide and support the service for you.',
        'You confirm that you have the right to upload Customer Data and that doing so does not breach any confidentiality obligation or law. How we handle personal data is described in our Privacy policy.',
      ],
    },
    {
      title: 'Acceptable use',
      body: [
        'You must not:',
      ],
      list: [
        'upload unlawful content, malware, or documents you have no right to share;',
        'attempt to access other customers’ data, or accounts other than your own;',
        'probe, scan, load-test or overload the service, or bypass its security, rate limits or usage limits;',
        'scrape the service or access it by automated means other than interfaces we provide;',
        'share sign-in credentials, or resell or sublicense access without our written consent;',
        'reverse engineer the service except where the law allows, or use it to build a competing product;',
        'use the service, or reports from it, to falsify, alter or misrepresent quality records, or to mislead a customer, inspector or authority;',
        'use the service in breach of applicable law, including export control and sanctions law.',
      ],
    },
    {
      title: 'Suspension',
      body: [
        'We may suspend access, in whole or in part, if we reasonably believe your use breaches these terms, puts the service or other customers at risk, or is required by law. Where practical we will tell you first and restore access once the issue is resolved.',
      ],
    },
    {
      title: 'Fees',
      body: ['Fees, billing periods and payment terms are set out in your order form. Unless stated otherwise, fees are exclusive of taxes and are non-refundable.'],
    },
    {
      title: 'Confidentiality',
      body: [
        'Each party will protect the other’s confidential information with at least reasonable care and use it only to perform under these terms. Customer Data is your confidential information.',
      ],
    },
    {
      title: 'Intellectual property',
      body: [
        'We own the service, including its software, rule sets and design. Reports you generate belong to you. If you send us feedback, we may use it without obligation to you.',
      ],
    },
    {
      title: 'Warranties and disclaimers',
      body: [
        'We will provide the service with reasonable skill and care. Otherwise, and to the extent permitted by law, the service is provided "as is" and "as available", without warranties of merchantability, fitness for a particular purpose or non-infringement.',
        'We do not warrant that extraction, mapping, checks or explanations will be complete or error-free, that the service will detect every missing or non-conforming record, or that it will be uninterrupted. Scanned, handwritten or low-quality documents may be read incorrectly.',
        'Demo projects, sample documents and features marked preview or beta are provided for evaluation only, without any commitment.',
      ],
    },
    {
      title: 'Third-party services',
      body: [
        'The service relies on third-party providers such as cloud hosting, storage, sign-in and document-processing services. We are not responsible for outages or changes caused by those providers, but we will choose them with care and work to restore service promptly.',
      ],
    },
    {
      title: 'Limitation of liability',
      body: [
        'To the extent permitted by law, neither party is liable for indirect or consequential loss, or for loss of profit, revenue or data. Each party’s total liability under these terms is limited to the fees paid or payable by your organisation in the twelve months before the claim. Nothing limits liability that cannot be limited by law.',
        'In particular, to the extent permitted by law, we are not liable for any loss arising from a release, acceptance or rejection decision made by you, from the failure of any product you fabricate, inspect or supply, or from your reliance on a report without verifying it against the source documents.',
      ],
    },
    {
      title: 'Indemnity',
      body: [
        'Your organisation will defend and indemnify us against third-party claims arising from Customer Data you upload, from your breach of the acceptable use rules, or from products you release, supply or certify, except to the extent the claim is caused by our breach of these terms.',
      ],
    },
    {
      title: 'Term and termination',
      body: [
        'These terms apply while you use the service. Either party may terminate for material breach not cured within 30 days of notice. On termination you may export your reports for 30 days, after which we delete Customer Data as described in the Privacy policy.',
      ],
    },
    {
      title: 'Force majeure',
      body: [
        'Neither party is liable for delay or failure caused by events beyond its reasonable control, such as natural disasters, war, labour disputes, power or network failures, or failures of third-party providers. This does not excuse payment obligations.',
      ],
    },
    {
      title: 'Governing law',
      body: ['These terms are governed by the laws of [jurisdiction]. The courts of [venue] have exclusive jurisdiction.'],
    },
    {
      title: 'General',
      body: [
        'If any part of these terms is found unenforceable, the rest remains in effect. A failure to enforce a right is not a waiver of it. You may not assign these terms without our consent; we may assign them to a successor of our business. These terms, with any order form, are the entire agreement between the parties about the service.',
      ],
    },
    {
      title: 'Changes',
      body: [
        'We may update these terms. We will post the new version here with a new effective date and, for material changes, notify account administrators at least 30 days in advance.',
      ],
    },
    {
      title: 'Contact',
      body: ['Questions about these terms: [legal@company.com].'],
    },
  ],
}

export const PRIVACY = {
  form: 'HBK-LEGAL-02',
  title: 'Privacy policy',
  lead: 'How Hibanako collects, uses and protects personal data when you visit the site, request a demo or use the service.',
  sections: [
    {
      title: 'Who we are',
      body: [
        '[Company legal name], [registered address], is the controller for personal data collected through this website and for account data. For documents your organisation uploads, your organisation is the controller and we process that data on its behalf.',
      ],
    },
    {
      title: 'What we collect',
      list: [
        'Demo requests: your work email address.',
        'Account data: name, work email, organisation and role, and sign-in records.',
        'Uploaded documents: certificates, weld records, inspection reports and similar files. These can contain personal data such as inspector names, welder IDs and signatures.',
        'Activity in the service: notes, sign-offs and decisions you record, with your name and time.',
        'Technical data: IP address, browser type and logs needed to run and secure the service.',
      ],
    },
    {
      title: 'How we use it',
      list: [
        'To provide the service: extracting data, building traceability maps, running checks and producing reports.',
        'To keep a reliable audit trail of who reviewed, noted and signed what.',
        'To respond to demo requests and support questions.',
        'To secure, maintain and improve the service.',
      ],
      body: ['We do not sell personal data and do not use uploaded documents for advertising.'],
    },
    {
      title: 'AI processing',
      body: [
        'Documents are read by AI models to extract data and to write explanations of findings. We use Google’s Gemini API for this, under Google’s API terms. [Confirm the data-use and retention terms of your Gemini API / Google Cloud plan and state them here.]',
        'This output is shown for review and does not decide release status. Verdicts come from deterministic rules, and sign-off is made by a person. Do not upload documents you are not permitted to share with these processors.',
      ],
    },
    {
      title: 'Sharing',
      body: [
        'We share personal data only with service providers that help us run Hibanako (for example cloud hosting and the AI provider above), under contracts that require them to protect it, and where the law requires it. A current list of subprocessors is available on request: [privacy@company.com].',
        'We may also disclose information where we believe in good faith it is needed to comply with law or a valid legal request, to enforce our terms, or to protect the rights, property or safety of Hibanako, our customers or others. If our business is merged or sold, data may transfer to the successor under this policy.',
      ],
    },
    {
      title: 'Retention',
      body: [
        'Account and project data is kept while your organisation’s subscription is active, and deleted within 90 days after it ends unless your organisation asks us to keep it longer or the law requires it. Demo request emails are kept for up to 24 months.',
      ],
    },
    {
      title: 'Security',
      body: [
        'Data is encrypted in transit and at rest. Access is limited to staff who need it to operate the service. Each customer’s documents are kept separate from other customers’ documents.',
        'No system is completely secure, and we cannot guarantee absolute security. You are responsible for keeping your credentials safe. If a breach affects your personal data, we will notify you and the relevant authorities as the law requires.',
      ],
    },
    {
      title: 'Your rights',
      body: [
        'Depending on where you are, you may have the right to access, correct, delete or export your personal data, to object to or restrict processing, and to complain to a data protection authority. For documents uploaded by your organisation, contact your administrator first. We will help them respond.',
      ],
    },
    {
      title: 'Usage and aggregated data',
      body: [
        'We may use aggregated or de-identified data about how the service is used, such as document counts, processing times and error rates, to operate and improve it. This data does not identify you, your organisation or the content of your documents.',
      ],
    },
    {
      title: 'Children',
      body: ['Hibanako is a business service and is not intended for anyone under 18. We do not knowingly collect personal data from children.'],
    },
    {
      title: 'International transfers',
      body: ['Where data is transferred across borders, we use appropriate safeguards such as standard contractual clauses.'],
    },
    {
      title: 'Cookies and local storage',
      body: [
        'Hibanako uses only what is needed to run the site: a session for signed-in users, and your light/dark display preference stored in your browser. We do not use advertising or cross-site tracking cookies.',
      ],
    },
    {
      title: 'Changes',
      body: ['We will post updates here with a new effective date and notify account administrators of material changes.'],
    },
    {
      title: 'Contact',
      body: ['Privacy questions or requests: [privacy@company.com].'],
    },
  ],
}
