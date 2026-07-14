using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.ComponentModel;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    [ObservableProperty]
    private INodeSpecializedEditorViewModel? selectedNodeSpecializedEditor;

    public bool HasSelectedNodeSpecializedEditor =>
        SelectedNodeSpecializedEditor is not null;

    public bool UsesGenericSelectedNodeConfigEditor =>
        SelectedNodeSpecializedEditor is null;

    public bool ShowsGenericSelectedNodeConfigEditor =>
        UsesGenericSelectedNodeConfigEditor
        && HasSelectedNodeConfigEditableInputFields;

    private void RebuildSelectedNodeSpecializedEditor()
    {
        INodeSpecializedEditorViewModel? editor = null;
        if (SelectedWorkflowDefinitionNode is not null
            && WorkflowDefinitionDetail is not null)
        {
            editor = NodeSpecializedEditorFactory.Create(
                SelectedWorkflowDefinitionNode.NodeEditorResolution.EditorKey,
                new NodeSpecializedEditorContext
                {
                    Node = SelectedWorkflowDefinitionNode,
                    Fields = SelectedNodeConfigEditableInputFields,
                    Connections = WorkflowDefinitionDetail.Connections,
                    CatalogService = _sharedPublicationCatalogService,
                    SqliteTableCatalogService = _sqliteTableCatalogService,
                    SqliteDatabaseFileService = _sqliteDatabaseFileService,
                    LocalizationService = _localizationService,
                    LifetimeToken = _shutdown.Token,
                });
        }

        ReplaceSelectedNodeSpecializedEditor(editor);
    }

    private void ReplaceSelectedNodeSpecializedEditor(
        INodeSpecializedEditorViewModel? editor)
    {
        if (ReferenceEquals(SelectedNodeSpecializedEditor, editor))
        {
            return;
        }

        if (SelectedNodeSpecializedEditor is not null)
        {
            SelectedNodeSpecializedEditor.ConfigChanged -=
                OnSelectedNodeSpecializedEditorConfigChanged;
            SelectedNodeSpecializedEditor.Dispose();
        }

        if (editor is not null)
        {
            editor.ConfigChanged += OnSelectedNodeSpecializedEditorConfigChanged;
        }

        SelectedNodeSpecializedEditor = editor;
    }

    partial void OnSelectedNodeSpecializedEditorChanged(
        INodeSpecializedEditorViewModel? value)
    {
        OnPropertyChanged(nameof(HasSelectedNodeSpecializedEditor));
        OnPropertyChanged(nameof(UsesGenericSelectedNodeConfigEditor));
        OnPropertyChanged(nameof(ShowsGenericSelectedNodeConfigEditor));
    }
}
