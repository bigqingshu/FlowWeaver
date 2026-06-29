using Avalonia_UI.Api;

namespace Avalonia_UI.ViewModels;

public sealed class SharedPublicationMemberListItemViewModel
{
    public SharedPublicationMemberListItemViewModel(
        SharedPublicationMemberDto member)
    {
        ExportName = member.ExportName;
        TableRefId = member.TableRefId;
        ExactTableVersion = member.ExactTableVersion;
    }

    public string ExportName { get; }

    public string TableRefId { get; }

    public int ExactTableVersion { get; }

    public string VersionText => $"v{ExactTableVersion}";
}
