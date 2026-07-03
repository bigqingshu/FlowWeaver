using System;
using System.IO;
using System.Linq;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class WorkflowSummaryViewStructureTests
{
    [TestMethod]
    public void NodeTemplateShowsEditorStatusAsReadOnlyText()
    {
        var xaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowSummaryView.axaml");

        StringAssert.Contains(xaml, "Text=\"{Binding NodeEditorStatusText}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding ConfigJson}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding SelectedNodeConfigDraftSummaryText}\"");
        StringAssert.Contains(xaml, "SelectedItem=\"{Binding SelectedWorkflowDefinitionNode}\"");
        StringAssert.Contains(xaml, "RowDefinitions=\"Auto,Auto,Auto,Auto\"");
        Assert.IsFalse(xaml.Contains("NodeEditorStatusText}\" Command=", StringComparison.Ordinal));
    }

    [TestMethod]
    public void NodeTemplateDoesNotIntroduceNodeEditingActions()
    {
        var xaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowSummaryView.axaml");

        Assert.IsFalse(xaml.Contains("EditNode", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("ConfigureNode", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("OpenNodeEditor", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("SaveNode", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("ListNodeDefinitionsAsync", StringComparison.Ordinal));
    }

    [TestMethod]
    public void NodeConfigEditorBindsToInputFieldsAndApplyCommand()
    {
        var xaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowSummaryView.axaml");

        StringAssert.Contains(
            xaml,
            "ItemsSource=\"{Binding SelectedNodeConfigEditableInputFields}\"");
        StringAssert.Contains(
            xaml,
            "Command=\"{Binding ApplySelectedNodeConfigDraftCommand}\"");
        StringAssert.Contains(
            xaml,
            "x:DataType=\"vm:NodeConfigEditableFieldInputViewModel\"");
        StringAssert.Contains(xaml, "Text=\"{Binding InputValue, Mode=TwoWay");
        StringAssert.Contains(xaml, "SelectedItem=\"{Binding InputValue, Mode=TwoWay}\"");
    }

    [TestMethod]
    public void NodeConfigEditorUsesViewHelperBindingsWithoutConverters()
    {
        var xaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowSummaryView.axaml");

        StringAssert.Contains(
            xaml,
            "IsVisible=\"{Binding HasSelectedNodeConfigEditableInputFields}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding DisplayLabel}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding TypeText}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding RequiredText}\"");
        StringAssert.Contains(xaml, "IsVisible=\"{Binding IsTextInput}\"");
        StringAssert.Contains(xaml, "IsVisible=\"{Binding IsEnumInput}\"");
        StringAssert.Contains(xaml, "IsVisible=\"{Binding IsBooleanInput}\"");
        StringAssert.Contains(xaml, "ItemsSource=\"{Binding BooleanValues}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding WarningText}\"");
        Assert.IsFalse(xaml.Contains("Converter=", StringComparison.Ordinal));
    }

    [TestMethod]
    public void StructuredEditFormsBindToDraftInputsAndCommands()
    {
        var xaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowSummaryView.axaml");

        StringAssert.Contains(xaml, "Text=\"{Binding AddNodeText}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding DeleteNodeText}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding AddConnectionText}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding DeleteConnectionText}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding NodeInstanceIdText}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding NodeTypeText}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding NodeVersionText}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding DisplayNameText}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding ConfigJsonText}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding NewDraftNodeInstanceId, Mode=TwoWay");
        StringAssert.Contains(xaml, "Text=\"{Binding NewDraftNodeType, Mode=TwoWay");
        StringAssert.Contains(xaml, "Text=\"{Binding NewDraftNodeVersion, Mode=TwoWay");
        StringAssert.Contains(xaml, "Text=\"{Binding NewDraftNodeDisplayName, Mode=TwoWay");
        StringAssert.Contains(xaml, "Text=\"{Binding NewDraftNodeConfigJson, Mode=TwoWay");
        StringAssert.Contains(
            xaml,
            "ItemsSource=\"{Binding NodeDefinitions}\"");
        StringAssert.Contains(
            xaml,
            "SelectedItem=\"{Binding SelectedNewDraftNodeDefinition, Mode=TwoWay}\"");
        StringAssert.Contains(
            xaml,
            "x:DataType=\"vm:NodeDefinitionListItemViewModel\"");
        StringAssert.Contains(
            xaml,
            "Command=\"{Binding AddWorkflowDefinitionDraftNodeCommand}\"");
        StringAssert.Contains(
            xaml,
            "Text=\"{Binding SelectedWorkflowDefinitionDraftNodeInstanceId, Mode=TwoWay");
        StringAssert.Contains(
            xaml,
            "Command=\"{Binding DeleteWorkflowDefinitionDraftNodeCommand}\"");

        StringAssert.Contains(xaml, "Text=\"{Binding ConnectionIdText}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding SourceNodeText}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding SourcePortText}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding TargetNodeText}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding TargetPortText}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding NewDraftConnectionId, Mode=TwoWay");
        StringAssert.Contains(xaml, "Text=\"{Binding NewDraftConnectionSourceNodeId, Mode=TwoWay");
        StringAssert.Contains(xaml, "Text=\"{Binding NewDraftConnectionSourcePort, Mode=TwoWay");
        StringAssert.Contains(xaml, "Text=\"{Binding NewDraftConnectionTargetNodeId, Mode=TwoWay");
        StringAssert.Contains(xaml, "Text=\"{Binding NewDraftConnectionTargetPort, Mode=TwoWay");
        StringAssert.Contains(
            xaml,
            "ItemsSource=\"{Binding WorkflowDefinitionDraftStructure.Nodes}\"");
        StringAssert.Contains(
            xaml,
            "SelectedItem=\"{Binding SelectedNewDraftConnectionSourceNode, Mode=TwoWay}\"");
        StringAssert.Contains(
            xaml,
            "SelectedItem=\"{Binding SelectedNewDraftConnectionTargetNode, Mode=TwoWay}\"");
        StringAssert.Contains(
            xaml,
            "x:DataType=\"models:WorkflowDefinitionDraftNode\"");
        StringAssert.Contains(xaml, "Text=\"{Binding NodeTypeDisplayName}\"");
        StringAssert.Contains(
            xaml,
            "Command=\"{Binding AddWorkflowDefinitionDraftConnectionCommand}\"");
        StringAssert.Contains(
            xaml,
            "Text=\"{Binding SelectedWorkflowDefinitionDraftConnectionId, Mode=TwoWay");
        StringAssert.Contains(
            xaml,
            "Command=\"{Binding DeleteWorkflowDefinitionDraftConnectionCommand}\"");
        Assert.IsFalse(xaml.Contains("Converter=", StringComparison.Ordinal));
    }

    [TestMethod]
    public void WorkflowDefinitionCardOmitsRevisionHistoryList()
    {
        var xaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowSummaryView.axaml");

        StringAssert.Contains(xaml, "Text=\"{Binding WorkflowDefinitionDetail.RevisionId}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding WorkflowDefinitionDetail.DefinitionHash}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding WorkflowDefinitionDetail.UpdatedAtText}\"");
        Assert.IsFalse(xaml.Contains("WorkflowDefinitionDetail.Revisions", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("WorkflowRevisionListItemViewModel", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("SelectedRevision", StringComparison.Ordinal));
    }

    [TestMethod]
    public void WorkflowPageKeepsDefinitionWorkspaceInTwoColumns()
    {
        var xaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Pages",
            "WorkflowPage.axaml");

        StringAssert.Contains(xaml, "ColumnDefinitions=\"340,*\"");
        StringAssert.Contains(xaml, "<workflow:WorkflowListView Grid.Column=\"0\" />");
        StringAssert.Contains(xaml, "<workflow:WorkflowSummaryView Grid.Column=\"1\" />");
        Assert.IsFalse(xaml.Contains("<workflow:WorkflowEditorView", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("<workflow:WorkflowNodeCatalogView", StringComparison.Ordinal));
    }

    [TestMethod]
    public void AdvancedDraftJsonIsToggledFromNodeActionArea()
    {
        var xaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowSummaryView.axaml");

        StringAssert.Contains(xaml, "Text=\"{Binding AdvancedDraftJsonText}\"");
        StringAssert.Contains(xaml, "Content=\"{Binding ShowAdvancedDraftJsonText}\"");
        StringAssert.Contains(
            xaml,
            "IsChecked=\"{Binding IsWorkflowDraftJsonAdvancedVisible, Mode=TwoWay}\"");
        StringAssert.Contains(
            xaml,
            "<workflow:WorkflowEditorView IsVisible=\"{Binding IsWorkflowDraftJsonAdvancedVisible}\"");

        var advancedToggleIndex = xaml.IndexOf(
            "Content=\"{Binding ShowAdvancedDraftJsonText}\"",
            StringComparison.Ordinal);
        var editorIndex = xaml.IndexOf(
            "<workflow:WorkflowEditorView IsVisible=\"{Binding IsWorkflowDraftJsonAdvancedVisible}\"",
            StringComparison.Ordinal);
        Assert.IsTrue(
            advancedToggleIndex >= 0 && editorIndex > advancedToggleIndex,
            "The draft JSON editor should remain behind the node action area's advanced toggle.");
    }

    [TestMethod]
    public void ConnectionsSectionIsCollapsedBehindToggleByDefault()
    {
        var xaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowSummaryView.axaml");

        StringAssert.Contains(xaml, "Content=\"{Binding ShowConnectionsText}\"");
        StringAssert.Contains(
            xaml,
            "IsChecked=\"{Binding IsWorkflowConnectionsAdvancedVisible, Mode=TwoWay}\"");
        StringAssert.Contains(
            xaml,
            "IsVisible=\"{Binding IsWorkflowConnectionsAdvancedVisible}\"");
        Assert.IsFalse(xaml.Contains("IsWorkflowConnectionsAdvancedVisible = true", StringComparison.Ordinal));
    }

    [TestMethod]
    public void MiddleColumnLayoutKeepsStructuredEditAreasCompactAndScrollable()
    {
        var xaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowSummaryView.axaml");

        StringAssert.Contains(xaml, "<ScrollViewer VerticalScrollBarVisibility=\"Auto\"");
        StringAssert.Contains(xaml, "<StackPanel Spacing=\"10\">");
        StringAssert.Contains(xaml, "MaxHeight=\"160\"");
        StringAssert.Contains(xaml, "MaxHeight=\"140\"");
        Assert.IsFalse(xaml.Contains("RowDefinitions=\"Auto,*,*\"", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("RowDefinitions=\"Auto,*,Auto,Auto,Auto\"", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("RowDefinitions=\"Auto,*,Auto\"", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("MinHeight=\"100\"", StringComparison.Ordinal));
    }

    private static string ReadSourceFile(params string[] pathParts)
    {
        var repoRoot = GetRepoRoot();
        return File.ReadAllText(Path.Combine(pathParts.Prepend(repoRoot).ToArray()));
    }

    private static string GetRepoRoot()
    {
        var directory = new DirectoryInfo(AppContext.BaseDirectory);
        while (directory is not null)
        {
            if (Directory.Exists(Path.Combine(directory.FullName, "Avalonia_UI"))
                && Directory.Exists(Path.Combine(directory.FullName, "Avalonia_UI.Tests")))
            {
                return directory.FullName;
            }

            directory = directory.Parent;
        }

        throw new DirectoryNotFoundException("Could not locate FlowWeaver repository root.");
    }
}
