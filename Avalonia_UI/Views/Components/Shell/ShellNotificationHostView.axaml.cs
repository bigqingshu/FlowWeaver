using Avalonia.Controls;
using Avalonia.Markup.Xaml;

namespace Avalonia_UI.Views.Components.Shell;

public partial class ShellNotificationHostView : UserControl
{
    public ShellNotificationHostView()
    {
        AvaloniaXamlLoader.Load(this);
    }
}
