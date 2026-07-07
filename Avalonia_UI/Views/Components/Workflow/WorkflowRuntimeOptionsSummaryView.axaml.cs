using Avalonia.Controls;
using Avalonia.Interactivity;
using Avalonia_UI.Views.Windows;

namespace Avalonia_UI.Views.Components.Workflow;

public partial class WorkflowRuntimeOptionsSummaryView : UserControl
{
    public WorkflowRuntimeOptionsSummaryView()
    {
        InitializeComponent();
    }

    private void OpenRuntimeOptionsWindow(object? sender, RoutedEventArgs e)
    {
        var window = new RuntimeOptionsEditorWindow
        {
            DataContext = DataContext,
        };
        if (TopLevel.GetTopLevel(this) is Window owner)
        {
            window.Show(owner);
            return;
        }

        window.Show();
    }
}
