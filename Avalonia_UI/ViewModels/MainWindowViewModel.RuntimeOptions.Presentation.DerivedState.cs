namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    public bool HasSelectedRuntimeOptionsNode => SelectedRuntimeOptionsNode is not null;

    public bool HasRuntimeOptionsEditorError =>
        !string.IsNullOrWhiteSpace(RuntimeOptionsEditorErrorMessage);
}
