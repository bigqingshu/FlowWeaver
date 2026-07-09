using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void ClearSelectedNewDraftConnectionNodesIfMissing()
    {
        if (SelectedNewDraftConnectionSourceNode is not null)
        {
            SelectedNewDraftConnectionSourceNode = FindDraftNode(
                SelectedNewDraftConnectionSourceNode.NodeInstanceId);
        }

        if (SelectedNewDraftConnectionTargetNode is not null)
        {
            SelectedNewDraftConnectionTargetNode = FindDraftNode(
                SelectedNewDraftConnectionTargetNode.NodeInstanceId);
        }
    }
}
