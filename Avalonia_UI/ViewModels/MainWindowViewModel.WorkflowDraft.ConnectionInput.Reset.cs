namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void ResetNewDraftConnectionInput()
    {
        lastSuggestedNewDraftConnectionId = string.Empty;
        SelectedNewDraftConnectionSourceNode = null;
        SelectedNewDraftConnectionTargetNode = null;
        NewDraftConnectionId = string.Empty;
        NewDraftConnectionSourceNodeId = string.Empty;
        NewDraftConnectionSourcePort = string.Empty;
        NewDraftConnectionTargetNodeId = string.Empty;
        NewDraftConnectionTargetPort = string.Empty;
    }
}
