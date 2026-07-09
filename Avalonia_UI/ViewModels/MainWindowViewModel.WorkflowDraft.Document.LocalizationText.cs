namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    public string WorkflowDefinitionSectionText => T("definition.section");

    public string DetailsText => T("definition.details");

    public string NameLabelText => T("definition.name");

    public string VersionLabelText => T("definition.version");

    public string RevisionLabelText => T("definition.revision");

    public string StatusLabelText => T("definition.status");

    public string HashLabelText => T("definition.hash");

    public string UpdatedLabelText => T("definition.updated");

    public string DraftJsonSectionText => T("definition.draft_json");

    public string ShowAdvancedDraftJsonText => IsWorkflowDraftJsonAdvancedVisible
        ? T("definition.hide_draft_json")
        : T("definition.show_draft_json");

    public string ValidateText => T("definition.validate");

    public string RestoreText => T("definition.restore");

    public string SaveText => T("definition.save");
}
