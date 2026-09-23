import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

void i18n.use(initReactI18next).init({
  lng: 'en', fallbackLng: 'en', interpolation: { escapeValue: false },
  resources: { en: { translation: {
    brand: 'Document Platform', workspace: 'Your workspace', eyebrow: 'A place for every document',
    heading: 'Good documents start here.', description: 'Explore your first template and make yourself at home.',
    templates: 'Templates', sample: 'Sample template', open: 'Explore template',
    loading: 'Loading your workspace...', error: 'We could not load your workspace. Please try again.',
    retry: 'Try again', empty: 'No templates yet.', status: 'Workspace status', ready: 'Connected',
    unavailable: 'Needs attention', database: 'Database', storage: 'Document storage', frontend: 'Application',
    starting: 'Checking connection', back: 'Back to templates', structure: 'Document structure',
    data: 'Sample data', future: 'Editing and document generation are coming in the next milestones.',
    letter: 'Welcome letter', letterDescription: 'A simple welcome letter with a recipient field and sample data.',
    footer: 'Your documents. Your infrastructure.', api: 'API reference', unknownStatus: 'Connection check unavailable',
    projectEyebrow: 'Delivery snapshot', projectStatus: 'Project status', statusSnapshot: 'Current foundation view', viewProjectStatus: 'View project status', backToWorkspace: 'Back to workspace', overallStatus: 'Overall status', overallProgress: 'Overall project progress', projectNote: 'Weights follow the number of source stories in each epic and total 100.0. Progress counts only evidence-backed implementation, not planned scope.', epicTableCaption: 'Epic stories and delivery status', storyId: 'Story ID', story: 'Story', priority: 'Priority', size: 'Size', weight: 'Weight', of: 'of', 'in-progress': 'In progress', planned: 'Planned',
    editorDraftNote: 'Local draft preview only. Saving and final document output will follow the template and rendering milestones.', editorToolbar: 'Text formatting controls', bold: 'Bold', italic: 'Italic', textColor: 'Text colour', alignment: 'Alignment', left: 'Left', center: 'Center', right: 'Right', addTextBlock: 'Add text block', textBlocks: 'Text blocks', selectBlock: 'Select text block', preview: 'Preview', localPreview: 'Local preview',
  } } },
})

export default i18n
