using Avalonia.Controls;
using Avalonia.Interactivity;

namespace Avalonia_UI.Views.Components.Workflow;

public partial class WorkflowListView : UserControl
{
    public WorkflowListView()
    {
        InitializeComponent();
    }

    private void CloseDeleteWorkflowConfirmFlyout(object? sender, RoutedEventArgs e)
    {
        DeleteWorkflowButton.Flyout?.Hide();
    }
}
